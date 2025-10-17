import threading

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from uuid import uuid4
import cv2, base64, numpy as np
from io import BytesIO
from PIL import Image
from ultralytics import YOLO
import uvicorn
from models import *
from yolo_class import YoloClass
import httpx

app = FastAPI()

# Настройка разрешенных доменов
origins = ["http://localhost:5173"]  # Сюда добавьте адреса вашего фронтенда

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Методы запросов, которые будут разрешены
    allow_headers=["*"],           # Разрешение любых заголовков
)

detection_dict = {}

# Папки для статики
STATIC_DIR = Path("static")
UPLOADS_DIR = STATIC_DIR / "uploads"
STATIC_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Раздача статики по /static/*
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Простейшее «хранилище» результатов в памяти
RESULTS_DB: List[Dict] = []


model: YOLO = YOLO("yolo11l")

NOMEROFF_URL = "http://localhost:8081/nomer"  # сервис A

def pil_to_bgr(img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)

def bgr_to_b64_jpg(img: np.ndarray) -> str:
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        raise RuntimeError("cv2.imencode failed")
    return base64.b64encode(buf.tobytes()).decode("utf-8")

def overlay_yolo(img_bgr: np.ndarray) -> np.ndarray:
    """Быстро нанесём YOLO-предсказания на картинку."""
    results = model(img_bgr)
    return results[0].plot()  # BGR ndarray

def overlay_plates(img_bgr: np.ndarray, detections: List[Dict]) -> np.ndarray:
    canvas = img_bgr.copy()
    for det in detections:
        if "bbox" in det:
            x1, y1, x2, y2 = map(int, det["bbox"])
            cv2.rectangle(canvas, (x1,y1), (x2,y2), (36,255,12), 2)
            if det.get("text"):
                cv2.putText(canvas, det["text"], (x1, max(0, y1-6)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (36,255,12), 2, cv2.LINE_AA)
    return canvas


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
    file: UploadFile = File(...),
):
    try:
        contents = await file.read()
        image = Image.open(BytesIO(contents)).convert("RGB")
        image_np = np.array(image)
        print(description)
        class_yolo = {
            "car": 2,
            "people": 0
        }
        # Детекция
        results = model(image_np, classes=[class_yolo.get(description, None)])
        plates = []
        if description in "Автомобиль":
            async with httpx.AsyncClient(timeout=30) as client:
                files = {
                    "file": (
                        file.filename, contents, file.content_type)
                }
                resp = await client.post(NOMEROFF_URL, files=files)
                print(resp)
                resp.raise_for_status()
                data = resp.json()
                print(data)
                plates = data["plates"]

        # Отрисованная картинка -> JPG буфер
        annotated = results[0].plot()  # ndarray (BGR)
        ok, buffer = cv2.imencode(".jpg", annotated)
        if not ok:
            raise RuntimeError("cv2.imencode failed")

        # === Сохраняем файл в static/uploads ===
        filename = f"{datetime.utcnow():%Y%m%d_%H%M%S}_{uuid4().hex}.jpg"
        file_path = UPLOADS_DIR / filename
        file_path.write_bytes(buffer.tobytes())

        # Относительная ссылка для фронта (именно такая нужна твоему getResults)
        link = f"static/uploads/{filename}"

        # Сохраняем запись в «базу результатов»
        record = {
            "Id": str(uuid4()),
            "Link": link,                       # фронт склеит http://localhost:5000/ + Link
            "Date": datetime.utcnow().isoformat(),
            "Title": title,
            "Description": plates,
            "Source": "-",                      # при необходимости — свой источник
        }
        RESULTS_DB.append(record)

        # Отправим и base64 (если нужно показать сразу) и путь для списка
        image_base64 = base64.b64encode(buffer).decode("utf-8")
        return JSONResponse({
            "title": title,
            "description": description,
            "annotated_image": image_base64,
            "link": link,                      # <- можно использовать на фронте сразу
        })

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Error processing image: {e}")
    finally:
        await file.close()

@app.get("/get-results")
def get_results():
    # Можно отсортировать по дате (свежие сверху)
    sorted_results = sorted(RESULTS_DB, key=lambda r: r["Date"], reverse=True)
    print(sorted_results)
    # Отдаём ключи так, как ждёт фронт: Id, Link, Date
    return [
        {
            "Id": r["Id"],
            "Link": r["Link"],  # например: static/uploads/20251016_…jpg
            "Date": r["Date"],
            "Title": r.get("Title", ""),
            "Description": r["Description"],
            "Source": r.get("Source", "-"),
        }
        for r in sorted_results
    ]



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
    uvicorn.run(app, port=8000)