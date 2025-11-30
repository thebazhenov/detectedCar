import threading
import redis
import httpx
import uvicorn
import base64
import cv2, base64, numpy as np
import time
import requests

from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends, status, Query, Response, WebSocket, WebSocketDisconnect
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Literal, Any
from uuid import uuid4
from io import BytesIO
from PIL import Image
from ultralytics import YOLO
from models import *
from update_yolo_class import YoloClass
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

app = FastAPI()
security = HTTPBasic()

redis_server = redis.Redis(host="localhost", port=6379, db=0)
CHATGPT_PLATE_URL = "http://localhost:8080/plate"


ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin"
ROLE_ADMIN = "admin"

# In-memory storage for active detections
detection_dict = {}

class StartDetectionRequest(BaseModel):
    source: str
    camera_id: str
    function_name: str
    skip_frames: Optional[int] = 5  # default to 1 if not provided

class StopDetectionRequest(BaseModel):
    camera_id: str



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

video_stream_manager = VideoStreamManager(DEMO_DIR, load_yolo_model)
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


class DemoVideoResponse(BaseModel):
    file_name: str
    file_url: str


def detection_response(settings: Dict[str, Any], mask_rtsp: bool = False) -> DetectionSettingsResponse:
    data = settings.copy()
    if mask_rtsp and data.get("rtspUrl"):
        data["rtspUrl"] = "***"
    return DetectionSettingsResponse(**data)

NOMEROFF_URL = "http://localhost:8182/nomer"  # сервис A

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

# ----------------------------------------------------------------------
# Эндпоинт: получить crop одного авто по vehicle_id
# ----------------------------------------------------------------------
@app.get("/vehicle/frame/{camera_id}/{vehicle_id}")
def get_vehicle_frame(camera_id: str, vehicle_id: int):
    detector = detection_dict.get(camera_id)
    if not detector:
        raise HTTPException(status_code=404, detail="Camera not active")

    frame = detector.vehicle_frames.get(vehicle_id)
    if not frame:
        raise HTTPException(status_code=404, detail="Vehicle frame not found")

    return Response(content=frame, media_type="image/jpeg")


# ----------------------------------------------------------------------
# Модель запроса для /vehicle/plate
# ----------------------------------------------------------------------
class PlateRequest(BaseModel):
    camera_id: str
    vehicle_id: int


# ----------------------------------------------------------------------
# Эндпоинт: определение номера у конкретного vehicle_id
# ----------------------------------------------------------------------
@app.post("/vehicle/plate")
async def get_vehicle_plate(payload: PlateRequest):

    detector = detection_dict.get(payload.camera_id)
    if not detector:
        raise HTTPException(status_code=404, detail="Camera not active")

    frame = detector.vehicle_frames.get(payload.vehicle_id)
    if not frame:
        raise HTTPException(status_code=404, detail="Vehicle frame not found")

    files = {
        "file": ("crop.jpg", frame, "image/jpeg")
    }

    async with httpx.AsyncClient(timeout=40) as client:
        resp = await client.post(CHATGPT_PLATE_URL, files=files)
        resp.raise_for_status()
        return resp.json()


class StartDetectionYolo(BaseModel):
    source: str           # путь к видео или rtsp
    camera_id: str
    skip_frames: int = 1
    resize_w: int | None = None
    resize_h: int | None = None

barrier = False


async def get_available():
    """Проверяет доступность номера, используя список из базы данных"""
    # Получаем список активных номеров из базы данных
    async with UnitOfWork()() as uow:
        available_plates = await uow.vehicles.get_active_plates()
    
    if not available_plates:
        return {"status": "no_vehicle"}  # Нет разрешенных номеров в базе

    # Ждем появления ключа в Redis (макс 30 секунд)
    timeout = 30
    interval = 0.5
    waited = 0
    data = None
    while waited < timeout:
        data = redis_server.get("vehicle_in")
        if data:
            break
        waited += interval
        await asyncio.sleep(interval)

    if not data:
        return {"status": "no_vehicle"}  # ключ так и не появился

    # Декодируем изображение
    nparr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    success, buffer = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 92])

    files = {"file": ("vehicle.jpg", buffer.tobytes(), "image/jpeg")}

    print(f"Отправка на {NOMEROFF_URL} ...")
    response = requests.post(NOMEROFF_URL, files=files)
    result = response.json()
    plates = result.get("plates", [])
    for plate in plates:
        for frame in plate:
            if frame in available_plates:
                return {"status": "available"}
    return {"status": "not_available"}

@app.get("/available_plate")
async def get_available_plate():
    return await get_available()


@app.get("/barrier/status")
def get_barrier_status():
    """Получить текущий статус шлагбаума из Redis"""
    status = redis_server.get("barrier_status")
    if status:
        return {"status": status.decode("utf-8")}
    return {"status": "down"}


def set_barrier_down_after_delay():
    """Установить шлагбаум в положение 'down' через 10 секунд"""
    time.sleep(10)
    redis_server.set("barrier_status", "down")


@app.get("/barrier/check")
async def check_and_raise_barrier():
    """Проверить доступность номера и автоматически поднять шлагбаум"""
    result = await get_available()
    
    if result.get("status") == "available":
        # Устанавливаем статус "up" в Redis
        redis_server.set("barrier_status", "up")
        
        # Запускаем поток для автоматического опускания через 10 секунд
        thread = threading.Thread(target=set_barrier_down_after_delay)
        thread.daemon = True
        thread.start()
        
        return {"status": "up", "message": "Шлагбаум поднят автоматически"}
    
    # Если не available, возвращаем текущий статус из Redis
    current_status = redis_server.get("barrier_status")
    if current_status:
        return {"status": current_status.decode("utf-8")}
    
    return {"status": "down"}


# ----------------------------------------------------------------------
# Эндпоинты для управления разрешенными номерами
# ----------------------------------------------------------------------

@app.get("/vehicles", response_model=list[VehicleRead])
async def list_vehicles(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    active_only: bool = Query(False),
    current_user: User = Depends(get_current_user)
):
    """Получить список разрешенных номеров"""
    async with UnitOfWork()() as uow:
        vehicles = await uow.vehicles.list(limit=limit, offset=offset, active_only=active_only)
        return vehicles


@app.post("/vehicles", response_model=VehicleRead, status_code=201)
async def create_vehicle(
    payload: VehicleCreate,
    current_user: User = Depends(get_current_user)
):
    """Добавить новый разрешенный номер"""
    async with UnitOfWork()() as uow:
        # Проверяем, не существует ли уже такой номер
        existing = await uow.vehicles.get_by_plate(payload.license_plate)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Номер {payload.license_plate} уже существует в базе"
            )
        vehicle = await uow.vehicles.create(payload)
        return vehicle


@app.get("/vehicles/plates")
async def get_active_plates(current_user: User = Depends(get_current_user)):
    """Получить список активных номеров для проверки доступа"""
    async with UnitOfWork()() as uow:
        plates = await uow.vehicles.get_active_plates()
        return {"plates": plates}


@app.post("/start_detection")
def start_detection(payload: StartDetectionYolo):

    resize = None
    if payload.resize_w and payload.resize_h:
        resize = (payload.resize_w, payload.resize_h)

    detector = YoloClass(
        source=payload.source,
        camera_id=payload.camera_id,
        skip_frames=payload.skip_frames,
        resize=resize,
        model_path="yolo11n.pt"
    )
    detector.set_region((678, 186, 1055, 471))
    detection_dict[payload.camera_id] = detector

    import threading
    thread = threading.Thread(target=detector.run, daemon=True)
    thread.start()

    return {"message": f"Detection started for camera {payload.camera_id}"}


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


@app.get("/", response_model=dict)
def root_healthcheck():
    return {"status": "ok"}


def _latest_demo_video() -> Optional[Path]:
    files = sorted(
        [f for f in DEMO_DIR.iterdir() if f.is_file()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return files[0] if files else None


@app.get("/demo/video", response_model=DemoVideoResponse)
def get_demo_video_metadata(current_user: User = Depends(get_current_user)):
    ensure_admin_user(current_user)
    latest = _latest_demo_video()
    if not latest:
        raise HTTPException(status_code=404, detail="Demo video not found")
    return _demo_video_response(latest.name)


@app.get("/demo/video/public", response_model=DemoVideoResponse)
def get_demo_video_public():
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
    """Return latest frame as image/jpeg."""
    data = video_stream_manager.get_frame_bytes()
    return Response(content=data, media_type="image/jpeg")


@app.websocket("/ws/video")
async def websocket_video(websocket: WebSocket, token: str = Query(..., alias="token")):
    """WebSocket endpoint that streams base64-encoded JPEG frames."""
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

class StopDetectionYolo(BaseModel):
    camera_id: str

@app.post("/stop_detection")
def stop_detection(payload: StopDetectionYolo):

    detector = detection_dict.get(payload.camera_id)
    if detector:
        detector.stop()
        del detection_dict[payload.camera_id]
        return {"message": f"Detection stopped for {payload.camera_id}"}

    raise HTTPException(status_code=404, detail="Camera not found")

def generate_processed(camera_id):
    stream_start_date = datetime.now().date()

    while True:
        if datetime.now().date() != stream_start_date:
            break

        # читаем обработанный кадр
        frame = redis_server.get(f"{camera_id}_processed_frame")
        flag = redis_server.get(f"{camera_id}_processed_flag")

        # Redis → bytes, поэтому сравнение с b"1"
        if flag == b"1" and frame:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" +
                frame +
                b"\r\n"
            )

        time.sleep(0.03)   # ~30 FPS



@app.get("/video_feed/{camera_id}")
def video_feed(camera_id: str):
    return StreamingResponse(
        generate_processed(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

if __name__ == "__main__":
    uvicorn.run(app, port=8000)