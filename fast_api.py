import uvicorn
from fastapi import FastAPI, HTTPException
from models import StartDetectionYolo, StopDetectionYolo
from yolo_class import YoloClass
import threading

app = FastAPI()

detection_dict = {}

@app.post("/start_detection")
def start_detection(detection: StartDetectionYolo):

    detection = YoloClass(detection.source, detection.camera_id, detection.function_name, detection.skip_frames)
    detection_dict[detection.camera_id]: YoloClass = detection

    thread = threading.Thread(target=detection.run)
    thread.start()

    return {
        "message": "Detection started"
    }

@app.post("/stop_detection")
def stop_detection(detection: StopDetectionYolo):

    if detection.camera_id in detection_dict:
        det = detection_dict.get(detection.camera_id)
        det.stop()
        del detection_dict[detection.camera_id]

        return {
            "message": f"Detection stopped for Camera ID {detection.camera_id}"
        }

    else:
        HTTPException(
            status_code=500
        )

if __name__ == "__main__":
    uvicorn.run(app)