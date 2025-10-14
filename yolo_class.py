import cv2
from ultralytics import YOLO
from ultralytics.utils.plotting import Annotator, colors
from utils.model_list import model_list


class YoloClass:
    def __init__(self, source, camera_id, function_name, skip_frames):
        self.videocapture = cv2.VideoCapture(source) # 0 - вебкамера, можно использовать путь к видео либо ртсп-ссылку
        self.model = YOLO(model_list[function_name]["model"])
        self.yolo_classes = model_list[function_name]["classes"]
        self.camera_id = camera_id
        self.skip_frames = skip_frames
        self.frame_counter = 0
        self.frame = None
        self.function_name = function_name
        self.detection_status = True
        print("init finished")

    def detect_people_with_phones(self):
        results = self.model(
            self.frame,
            classes=self.yolo_classes
        )
        if results[0].boxes is not None:
            boxes = results[0].boxes.xyxy.cpu()
            names = results[0].names
            clss = results[0].boxes.cls.cpu().tolist()
            annotator = Annotator(self.frame, line_width=2)
            for box, cls in zip(boxes, clss):
                annotator.box_label(box, str(names[cls]), color=colors(cls, True))

    def detect_cars(self):
        results = self.model(self.frame)

    def run(self):
        while self.detection_status:
            print("In while")
            # Если не прошло skip_frames кадров, то пропускаем кадр
            if self.frame_counter % self.skip_frames != 0:
                self.videocapture.grab()
                self.frame_counter += 1
                continue
            
            ret, frame = self.videocapture.read()
            if ret:
                self.frame = frame
                self.frame_counter += 1
                
                if self.function_name == 'detect_people_with_phones':
                    self.detect_people_with_phones()
                elif self.function_name == 'detect_cars':
                    self.detect_cars()
                    
                # show frame
                cv2.imshow(f'Camera {self.camera_id}', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                continue
        self.videocapture.release()
        cv2.destroyAllWindows()
    
    def stop(self):
        self.detection_status = False
