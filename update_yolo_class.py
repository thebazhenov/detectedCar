import cv2
import redis
import numpy as np
from ultralytics import YOLO
from ultralytics.utils.plotting import Annotator, colors
from typing import Optional, List, Tuple, Union
import os
from datetime import datetime

RegionType = Union[Tuple[int, int, int, int], List[Tuple[int, int]]]


class YoloClass:
    """
    YOLO детектор с трекингом, сохранением crop по vehicle_id и поддержкой региона отображения.

    region может быть:
      - None (без региона)
      - прямоугольник: (x1, y1, x2, y2)
      - многоугольник: [(x1, y1), (x2, y2), ...]
    """

    def __init__(
        self,
        source,
        camera_id,
        skip_frames=1,
        resize=None,
        model_path="yolo_model.pt",
        region: Optional[RegionType] = None,
    ):
        self.source = source
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

        # сохранения кадра по id
        self.vehicle_frames = {}  # vehicle_id -> jpeg bytes

        # Redis для стриминга
        self.redis_server = redis.Redis(host="localhost", port=6379, db=0)

        # Регион (None, rect, or polygon)
        self.region = None
        if region is not None:
            self.set_region(region)

        print("🚀 YoloClass инициализирован — детекция транспорта с трекингом и регионом")

    # ---------------------- region helpers ----------------------
    def set_region(self, region: RegionType):
        """
        region:
          - (x1, y1, x2, y2)  -> rectangle
          - [(x1,y1), (x2,y2), ...] -> polygon
        """
        if isinstance(region, tuple) and len(region) == 4:
            x1, y1, x2, y2 = region
            pts = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.int32)
        else:
            # assume polygon-like list of tuples
            pts = np.array(region, dtype=np.int32)

        # ensure shape (N, 2)
        if pts.ndim != 2 or pts.shape[1] != 2:
            raise ValueError("region must be (x1,y1,x2,y2) or list of (x,y) tuples")

        self.region = pts

    def clear_region(self):
        self.region = None

    def _is_point_in_region(self, x: int, y: int) -> bool:
        """Возвращает True если точка внутри region. Если region отсутствует - False."""
        if self.region is None:
            return False
        # cv2.pointPolygonTest принимает contour как Nx2 или Nx1x2
        return cv2.pointPolygonTest(self.region, (int(x), int(y)), False) >= 0

    # ------------------------------------------------------------------
    # Основная детекция + трекинг
    # ------------------------------------------------------------------
    def detect_and_track(self, frame):
        results = self.model.track(frame, persist=True, classes=self.car_classes)

        any_vehicle_in_region = False
        tracked_objects = []

        boxes = results[0].boxes.xyxy.cpu().numpy()
        ids = results[0].boxes.id
        clss = results[0].boxes.cls.cpu().numpy()
        names = results[0].names

        if ids is not None:
            ids = ids.cpu().numpy()

        annotator = Annotator(frame.copy(), line_width=2)

        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = map(int, box)
            cls = int(clss[i])
            obj_id = int(ids[i]) if ids is not None else None

            # центр
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)

            in_region = self._is_point_in_region(cx, cy) if self.region is not None else False
            if in_region:
                any_vehicle_in_region = True

            # рисование бокса
            box_color = colors(cls, True)
            label = f"{names[cls]}"
            if obj_id is not None:
                label += f" ID:{obj_id}"
            label += f" {'IN' if in_region else 'OUT'}"

            annotator.box_label([x1, y1, x2, y2], label, color=box_color)

            tracked_objects.append({
                "id": obj_id,
                "bbox": [x1, y1, x2, y2],
                "in_region": in_region
            })

        annotated = annotator.result()
        annotated = self._draw_region_overlay(annotated)

        # ---- Проверяем, есть ли активное транспортное средство в регионе ----
        if not hasattr(self, "vehicle_active_in_region"):
            self.vehicle_active_in_region = False

        if any_vehicle_in_region and not self.vehicle_active_in_region:
            # Сохраняем кадр один раз при первом появлении
            ok, buf = cv2.imencode(".jpg", frame)
            if ok:
                self.redis_server.set("vehicle_in", buf.tobytes())
                os.makedirs("detect_image", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                filename = f"detect_image/vehicle_{timestamp}.jpg"
                cv2.imwrite(filename, frame)
            self.vehicle_active_in_region = True
        elif not any_vehicle_in_region and self.vehicle_active_in_region:
            # Автомобиль ушел — сбрасываем состояние
            self.redis_server.delete("vehicle_in")
            self.vehicle_active_in_region = False

        return annotated, tracked_objects

    # ------------------------------------------------------------------
    # region drawing
    # ------------------------------------------------------------------
    def _draw_region_overlay(self, img: np.ndarray) -> np.ndarray:
        """Рисует полупрозрачный регион и контур. Возвращает изображение."""
        if self.region is None:
            return img

        overlay = img.copy()
        out = img.copy()

        # fill region with alpha
        pts = self.region.reshape((-1, 1, 2))
        cv2.fillPoly(overlay, [pts], color=(0, 255, 0))  # fill (will be blended)
        alpha = 0.15
        cv2.addWeighted(overlay, alpha, out, 1 - alpha, 0, out)

        # draw polygon border thicker
        cv2.polylines(out, [pts], isClosed=True, color=(0, 255, 0), thickness=2)

        # label region in top-left corner of bbox of region
        x, y, w, h = cv2.boundingRect(pts)
        text = "Region"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 1
        (tw, th), _ = cv2.getTextSize(text, font, font_scale, thickness)
        # text background
        cv2.rectangle(out, (x, y - th - 8), (x + tw + 8, y), (0, 255, 0), -1)
        cv2.putText(out, text, (x + 4, y - 6), font, font_scale, (0, 0, 0), thickness, cv2.LINE_AA)

        return out

    # ------------------------------------------------------------------
    # Основной цикл
    # ------------------------------------------------------------------
    def run(self):
        while self.detection_status:

            if self.frame_counter % self.skip_frames != 0:
                self.videocapture.grab()
                self.frame_counter += 1
                continue

            ret, frame = self.videocapture.read()

            if not ret:
                self.videocapture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            if self.resize:
                w, h = self.resize
                frame = cv2.resize(frame, (w, h))

            self.frame = frame
            self.frame_counter += 1

            # RAW frame → Redis
            ok_raw, encoded_raw = cv2.imencode(".jpg", frame)
            if ok_raw:
                self.redis_server.set(f"{self.camera_id}_stream_frame", encoded_raw.tobytes())
                self.redis_server.set(f"{self.camera_id}_stream_flag", 1)

            # DETECT + TRACK
            processed, tracked = self.detect_and_track(frame)

            # Save processed frame
            ok_p, enc_p = cv2.imencode(".jpg", processed)
            if ok_p:
                self.redis_server.set(f"{self.camera_id}_processed_frame", enc_p.tobytes())
                self.redis_server.set(f"{self.camera_id}_processed_flag", 1)

            # Show window
            cv2.imshow(f"Camera {self.camera_id}", processed)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        self.videocapture.release()
        cv2.destroyAllWindows()

    def stop(self):
        self.detection_status = False
