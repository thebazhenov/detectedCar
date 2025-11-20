import threading

from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends, status, Query, Response, WebSocket, WebSocketDisconnect
import asyncio
import base64
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Literal, Any
from uuid import uuid4
import cv2, base64, numpy as np
from io import BytesIO
from PIL import Image
from ultralytics import YOLO
import uvicorn
from models import *
from yolo_class import YoloClass
import httpx
from pydantic import BaseModel, Field

from database.schemas import *
from database.uow import UnitOfWork
from database.models import User

from utils.settings_manager import (
    load_detection_settings,
    update_detection_settings,
    get_public_detection_settings,
)
from utils.video_stream import VideoStreamManager
import os
try:
    import redis
except Exception:
    redis = None

app = FastAPI()
security = HTTPBasic()
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin"
ROLE_ADMIN = "admin"


def ensure_admin_user(user: User):
    if user.role != ROLE_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

@app.on_event("startup")
async def _ensure_admin_and_demo():
    # Try to create admin user if DB is reachable
    try:
        async with UnitOfWork()() as uow:
            existing = await uow.users.by_email(ADMIN_EMAIL)
            if not existing:
                await uow.users.create(UserCreate(email=ADMIN_EMAIL, password=ADMIN_PASSWORD, role=ROLE_ADMIN))
    except Exception as e:
        print(f"Startup DB check skipped: {e}")

    # On startup, if detection source not configured, select latest demo video automatically
    try:
        current = load_detection_settings()
        if current.get("sourceType") is None:
            latest = _latest_demo_video()
            if latest:
                resp = _demo_video_response(latest.name)
                updated = update_detection_settings(
                    {
                        "sourceType": "file",
                        "videoPath": resp["file_url"],
                        "videoFileName": latest.name,
                    }
                )
                # ensure video manager picks up new settings
                try:
                    video_stream_manager.update_settings(updated)
                except Exception:
                    pass
    except Exception as e:
        print(f"Startup demo selection skipped: {e}")


@app.on_event("startup")
async def ensure_admin_exists():
    # Run the startup tasks but don't let DB/connectivity issues block startup.
    try:
        await asyncio.wait_for(_ensure_admin_and_demo(), timeout=5.0)
    except asyncio.TimeoutError:
        print("Startup tasks timed out (DB likely unavailable). Continuing without DB initialization.")
    except Exception as e:
        print(f"Unexpected error during startup tasks: {e}")

# Настройка разрешенных доменов
origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    # Vite / React dev server defaults
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    # Common dev ports
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]  

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Or specify: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers=["*"],  # Or specify: ["Content-Type", "Authorization"]
)


detection_dict = {}

# Папки для статики и моделей
STATIC_DIR = Path("static")
UPLOADS_DIR = STATIC_DIR / "uploads"
DEMO_DIR = Path("demo")
DEMO_STATIC_ROUTE = "/demo-files"
YOLO_MODELS_DIR = Path("models") / "yolo"
DEFAULT_YOLO_MODEL = "yolo11l.pt"

STATIC_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
DEMO_DIR.mkdir(exist_ok=True)
YOLO_MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Раздача статики по /static/* и /demo-files/*
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount(DEMO_STATIC_ROUTE, StaticFiles(directory=str(DEMO_DIR)), name="demo-files")

ALLOWED_DEMO_VIDEO_TYPES = {"video/mp4", "video/webm", "video/ogg"}
MAX_DEMO_VIDEO_SIZE_MB = 200

# Простейшее «хранилище» результатов в памяти
RESULTS_DB: List[Dict] = []


def resolve_model_path(model_name: str) -> Path:
    candidate = YOLO_MODELS_DIR / model_name
    if candidate.exists():
        return candidate
    fallback = YOLO_MODELS_DIR / DEFAULT_YOLO_MODEL
    if fallback.exists():
        return fallback
    return Path(DEFAULT_YOLO_MODEL)


def load_yolo_model(model_name: str) -> YOLO:
    model_path = resolve_model_path(model_name)
    return YOLO(str(model_path))


current_detection_settings = load_detection_settings()
# model is loaded lazily to avoid blocking startup
model_name = current_detection_settings.get("detectionModel", DEFAULT_YOLO_MODEL)
model: Optional[YOLO] = None

def get_model() -> YOLO:
    global model
    global model_name
    if model is None:
        try:
            model = load_yolo_model(model_name)
        except Exception as e:
            print(f"Failed to load YOLO model '{model_name}': {e}")
            raise
    return model

# Try to initialize Redis client if available via REDIS_URL env var
redis_client = None
if redis is not None:
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = redis.Redis.from_url(redis_url)
    except Exception:
        redis_client = None

video_stream_manager = VideoStreamManager(DEMO_DIR, load_yolo_model, redis_client=redis_client)
video_stream_manager.update_settings(current_detection_settings, restart=False)


class WidgetPreferencesPayload(BaseModel):
    videoWidget: Optional[bool] = Field(default=None)
    accessButton: Optional[bool] = Field(default=None)


class WidgetPreferences(BaseModel):
    videoWidget: bool = True
    accessButton: bool = True


class DetectionSettingsResponse(BaseModel):
    sourceType: Optional[Literal["rtsp", "file"]] = None
    rtspUrl: str = ""
    videoPath: str = ""
    videoFileName: str = ""
    detectionTarget: Literal["vehicles", "people"] = "vehicles"
    detectionModel: str = DEFAULT_YOLO_MODEL
    widgets: WidgetPreferences = WidgetPreferences()


class DetectionSettingsUpdatePayload(BaseModel):
    sourceType: Optional[Literal["rtsp", "file", None]] = None
    rtspUrl: Optional[str] = None
    videoPath: Optional[str] = None
    videoFileName: Optional[str] = None
    detectionTarget: Optional[Literal["vehicles", "people"]] = None
    detectionModel: Optional[str] = None
    widgets: Optional[WidgetPreferencesPayload] = None


def detection_response(settings: Dict[str, Any], mask_rtsp: bool = False) -> DetectionSettingsResponse:
    data = settings.copy()
    if mask_rtsp and data.get("rtspUrl"):
        data["rtspUrl"] = "***"
    return DetectionSettingsResponse(**data)

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
    try:
        m = get_model()
    except Exception:
        return img_bgr
    results = m(img_bgr)
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


async def get_current_user(credentials: HTTPBasicCredentials = Depends(security)) -> User:
    async with UnitOfWork()() as uow:
        user = await uow.users.check_credentials(credentials.username, credentials.password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return user


async def authenticate_token(token: str) -> User:
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        decoded = base64.b64decode(token).decode("utf-8")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    if ":" not in decoded:
        raise HTTPException(status_code=401, detail="Invalid token format")
    username, password = decoded.split(":", 1)
    async with UnitOfWork()() as uow:
        user = await uow.users.check_credentials(username, password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return user


@app.post("/users", response_model=UserRead, status_code=201)
async def create_user(payload: UserCreate, current_user: User = Depends(get_current_user)):
    ensure_admin_user(current_user)
    async with UnitOfWork()() as uow:
        existing = await uow.users.by_email(payload.email)
        if existing:
            raise HTTPException(status_code=409, detail="User already exists")
        user = await uow.users.create(payload)
        return user


@app.get("/users", response_model=list[UserRead])
async def list_users(limit: int = 50, offset: int = 0, current_user: User = Depends(get_current_user)):
    ensure_admin_user(current_user)
    """Возвращает список пользователей с пагинацией."""
    async with UnitOfWork()() as uow:
        users = await uow.users.list(limit=limit, offset=offset)
        return users


@app.post("/auth", response_model=UserRead)
async def auth_user(payload: AuthRequest):
    async with UnitOfWork()() as uow:
        user = await uow.users.check_credentials(payload.email, payload.password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        return user


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
        try:
            m = get_model()
            results = m(image_np, classes=[class_yolo.get(description, None)])
        except Exception as e:
            print(f"YOLO inference skipped: {e}")
            results = []
        plates = []
        if description in "car":
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
        if not results:
            annotated = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        else:
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


@app.get("/settings/detection", response_model=DetectionSettingsResponse)
async def get_detection_settings_endpoint(current_user: User = Depends(get_current_user)):
    ensure_admin_user(current_user)
    settings = load_detection_settings()
    return detection_response(settings)


@app.get("/settings/detection/public", response_model=DetectionSettingsResponse)
async def get_public_detection_settings_endpoint(current_user: User = Depends(get_current_user)):
    settings = get_public_detection_settings()
    return detection_response(settings, mask_rtsp=True)


@app.patch("/settings/detection", response_model=DetectionSettingsResponse)
async def patch_detection_settings(
    payload: DetectionSettingsUpdatePayload,
    current_user: User = Depends(get_current_user),
):
    ensure_admin_user(current_user)
    global model
    partial = payload.model_dump(exclude_unset=True)
    widgets = partial.get("widgets")
    if widgets:
        partial["widgets"] = {k: v for k, v in widgets.items() if v is not None}
    updated = update_detection_settings(partial)

    if "detectionModel" in partial:
        video_stream_manager.update_model(updated["detectionModel"], restart=False)
        # update model name and reset cached model so it will be loaded lazily
        model_name = updated["detectionModel"]
        model = None

    video_stream_manager.update_settings(updated)

    return detection_response(updated)


def _demo_video_response(file_name: str) -> Dict[str, str]:
    return {
        "file_name": file_name,
        "file_url": f"{DEMO_STATIC_ROUTE}/{file_name}",
    }


def _latest_demo_video() -> Optional[Path]:
    files = sorted(
        [f for f in DEMO_DIR.iterdir() if f.is_file()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return files[0] if files else None


@app.get("/demo/video")
def get_demo_video_metadata(current_user: User = Depends(get_current_user)):
    ensure_admin_user(current_user)
    latest = _latest_demo_video()
    if not latest:
        raise HTTPException(status_code=404, detail="Demo video not found")
    return _demo_video_response(latest.name)


@app.post("/demo/video")
async def upload_demo_video(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    # Uploading demo videos is disabled — demo files should be placed directly into the
    # `demo/` directory on the server. Return 405 to signal that uploads are not permitted.
    ensure_admin_user(current_user)
    raise HTTPException(status_code=405, detail="Uploading demo videos is disabled; place files in the server demo/ directory")


@app.delete("/demo/video/{file_name}")
async def delete_demo_video(
    file_name: str,
    current_user: User = Depends(get_current_user),
):
    ensure_admin_user(current_user)
    safe_name = Path(file_name).name
    target = DEMO_DIR / safe_name
    if not target.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    target.unlink()
    settings = load_detection_settings()
    if settings.get("videoFileName") == safe_name:
        updated = update_detection_settings(
            {
                "sourceType": None,
                "videoPath": "",
                "videoFileName": "",
            }
        )
        video_stream_manager.update_settings(updated)
    return {"detail": "Deleted"}


def _list_yolo_models() -> List[Dict]:
    models = []
    for file in sorted(YOLO_MODELS_DIR.glob("*.pt")):
        stats = file.stat()
        size_mb = round(stats.st_size / (1024 * 1024), 2)
        models.append(
            {
                "file_name": file.name,
                "display_name": file.stem.replace("_", " ").title(),
                "size_mb": size_mb,
            }
        )
    return models


@app.get("/models/yolo")
def get_yolo_models(current_user: User = Depends(get_current_user)):
    ensure_admin_user(current_user)
    return _list_yolo_models()


@app.get("/video/stream")
async def video_stream(token: str = Query(..., alias="token")):
    await authenticate_token(token)
    generator = video_stream_manager.stream()
    return StreamingResponse(generator, media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/video/frame")
def get_latest_frame():
    """Return latest frame as image/jpeg.

    This endpoint first attempts to read the latest frame from Redis (if configured).
    If Redis is not available or no frame is cached, it falls back to the in-memory frame.
    """
    # Try Redis first
    if redis is not None and redis_client is not None:
        try:
            data = redis_client.get("video:latest_frame")
            if data:
                return Response(content=data, media_type="image/jpeg")
        except Exception:
            pass

    # Fallback to in-memory frame
    data = video_stream_manager.get_frame_bytes()
    return Response(content=data, media_type="image/jpeg")


@app.websocket("/ws/video")
async def websocket_video(websocket: WebSocket, token: str = Query(..., alias="token")):
    """WebSocket endpoint that streams base64-encoded JPEG frames.

    Authentication: expects `token` query param (same token format as `/video/stream`).
    The handler will attempt to read frames from Redis first, otherwise from in-memory latest frame.
    """
    # Accept and then authenticate
    await websocket.accept()
    try:
        await authenticate_token(token)
    except Exception:
        await websocket.close(code=1008)
        return

    # Ensure producer is running
    try:
        video_stream_manager.start()
    except Exception:
        pass

    try:
        while True:
            # Try Redis first
            data = None
            if redis is not None and redis_client is not None:
                try:
                    data = redis_client.get("video:latest_frame")
                except Exception:
                    data = None
            if not data:
                data = video_stream_manager.get_frame_bytes()

            if data:
                try:
                    b64 = base64.b64encode(data).decode("ascii")
                    await websocket.send_text(b64)
                except Exception:
                    # If sending fails, break to close socket
                    break

            await asyncio.sleep(0.05)

    except WebSocketDisconnect:
        return
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass
        return



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