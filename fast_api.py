import uvicorn
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.responses import JSONResponse
from models import StartDetectionYolo, StopDetectionYolo, ImageData
from yolo_class import YoloClass
import threading
from ultralytics import YOLO
from io import BytesIO
from PIL import Image
import cv2
import numpy as np
import base64
from fastapi.responses import StreamingResponse
import io
from typing import Optional, List, Dict

app = FastAPI()

detection_dict = {}

model = YOLO("yolo11l")

@app.post("/start_detection")
def start_detection(detection: StartDetectionYolo):

    detection = YoloClass(int(detection.source), detection.camera_id, detection.function_name, detection.skip_frames)
    detection_dict[detection.camera_id]: YoloClass = detection

    thread = threading.Thread(target=detection.run)
    thread.start()

    return {
        "message": "Detection started"
    }

@app.post("/detect_image")
async def detect_objects(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...)
):
    try:
        # читаем байты файла
        contents = await file.read()
        image = Image.open(BytesIO(contents)).convert("RGB")
        image_np = np.array(image)

        # детекция
        results = model(image_np)

        detections: List[Dict] = []
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                confidence = float(box.conf.item())
                class_id = int(box.cls.item())
                class_name = model.names[class_id]
                detections.append({
                    "class": class_name,
                    "confidence": confidence,
                    "bbox": [x1, y1, x2, y2],
                })

        # отрисованное изображение -> jpg -> base64
        annotated_image = results[0].plot()
        ok, buffer = cv2.imencode(".jpg", annotated_image)
        if not ok:
            raise RuntimeError("cv2.imencode failed")

        image_base64 = base64.b64encode(buffer).decode("utf-8")

        return JSONResponse({
            "title": title,
            "description": description,
            "detections": detections,
            "annotated_image": image_base64,  # строка base64
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {e}")
    finally:
        await file.close()



    # @app.post("/upload_image/")
    # async def upload_image(file: Annotated[UploadFile, File(...)]):
    #     contents = await file.read()  # Читаем содержимое файла
    #     filename = file.filename  # Получаем оригинальное имя файла
    #     content_type = file.content_type  # Тип содержимого (например, image/jpeg)
    #
    #     # Здесь можем сохранить файл или обработать его
    #     with open(filename, "wb") as f:
    #         f.write(contents)
    #
    #     return {"filename": filename, "content-type": content_type}


# Добавляем обработчик для метода OPTIONS
@app.options("/start_detection")
async def options_start_detection(request):
    headers = request.headers.get("Access-Control-Request-Headers")
    if headers is not None:
        return {"headers": headers}

    return {"message": "Options available"}


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