import cv2
import copy
import redis
from ultralytics import YOLO
from ultralytics.utils.plotting import Annotator, colors


class YoloClass:
    def __init__(self, source, camera_id, skip_frames=1, resize=None, model_path="yolo_model.pt"):
        self.videocapture = cv2.VideoCapture(source)
        if not self.videocapture.isOpened():
            raise RuntimeError(f"❌ Не удалось открыть видеоисточник: {source}")

        self.model = YOLO(model_path)

        # COCO classes: 2-car, 3-motorcycle, 5-bus, 7-truck
        self.car_classes = [2, 3, 5, 7]

        self.camera_id = camera_id
        self.skip_frames = skip_frames
        self.frame_counter = 0
        self.frame = None
        self.detection_status = True
        self.resize = resize

        self.redis_server = redis.Redis(host="localhost", port=6379, db=0)

        print("🚀 YoloClass инициализирован — детекция ТОЛЬКО транспорта")

    # ---------------------------------------------------
    # 🚗 ДЕТЕКЦИЯ ТОЛЬКО МАШИН (возвращает обработанный кадр)
    # ---------------------------------------------------
    def detect_cars(self):
        results = self.model(self.frame, classes=self.car_classes)

        boxes = results[0].boxes
        if boxes is None:
            return self.frame

        annotated_frame = self.frame.copy()
        annotator = Annotator(annotated_frame, line_width=2)

        xyxy = boxes.xyxy.cpu()
        clss = boxes.cls.cpu().tolist()
        names = results[0].names

        for box, cls in zip(xyxy, clss):
            annotator.box_label(box, names[int(cls)], color=colors(int(cls), True))

        return annotated_frame

    # ---------------------------------------------------
    # 🔄 Основной цикл
    # ---------------------------------------------------
    def run(self):
        while self.detection_status:

            if self.frame_counter % self.skip_frames != 0:
                self.videocapture.grab()
                self.frame_counter += 1
                continue

            ret, frame = self.videocapture.read()
            if not ret:
                print("Видео закончилось или ошибка чтения.")
                break

            # Масштабирование
            if self.resize:
                w, h = self.resize
                frame = cv2.resize(frame, (w, h))

            self.frame = frame
            self.frame_counter += 1

            # ---------------------------------------------------
            # 1️⃣ Кодирование обычного (сырого) кадра
            # ---------------------------------------------------
            ok_raw, encoded_raw = cv2.imencode(".jpg", frame)
            if ok_raw:
                self.redis_server.set(f"{self.camera_id}_stream_frame", encoded_raw.tobytes())
                self.redis_server.set(f"{self.camera_id}_stream_flag", 1)
            else:
                self.redis_server.set(f"{self.camera_id}_stream_flag", 0)

            # ---------------------------------------------------
            # 2️⃣ Обработка кадра (детекция машин)
            # ---------------------------------------------------
            processed = self.detect_cars()

            # ---------------------------------------------------
            # 3️⃣ Сохранение ОБРАБОТАННОГО кадра в Redis
            # ---------------------------------------------------
            ok_processed, encoded_processed = cv2.imencode(".jpg", processed)
            if ok_processed:
                self.redis_server.set(f"{self.camera_id}_processed_frame", encoded_processed.tobytes())
                self.redis_server.set(f"{self.camera_id}_processed_flag", 1)
            else:
                self.redis_server.set(f"{self.camera_id}_processed_flag", 0)

            # ---------------------------------------------------
            # 4️⃣ Показываем обработанный кадр
            # ---------------------------------------------------
            cv2.imshow(f"Camera {self.camera_id}", processed)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        self.videocapture.release()
        cv2.destroyAllWindows()

    def stop(self):
        self.detection_status = False
