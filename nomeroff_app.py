from fastapi import FastAPI, UploadFile
from nomeroff_net import pipeline
import cv2
import numpy as np

app = FastAPI()

# Загружаем пайплайн распознавания номеров
nm_pipeline = pipeline("number_plate_detection_and_reading")

@app.post("/recognize")
async def recognize(file: UploadFile):
    # читаем байты
    image_bytes = await file.read()
    np_image = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(np_image, cv2.IMREAD_COLOR)

    # инференс
    results = nm_pipeline(frame)

    return {"plates": results}