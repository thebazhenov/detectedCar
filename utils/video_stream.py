import threading
import time
from pathlib import Path
from typing import Callable, Dict, Iterator, Optional

import cv2
import numpy as np
from ultralytics import YOLO

from utils.settings_manager import load_detection_settings

DETECTION_CLASS_MAP = {
    "vehicles": [2, 3, 5, 7],  # car, motorcycle, bus, truck
    "people": [0],
}

FRAME_BOUNDARY = b"--frame"


class VideoStreamManager:
    def __init__(
        self,
        demo_dir: Path,
        model_loader: Callable[[str], YOLO],
    ):
        self.demo_dir = demo_dir
        self.model_loader = model_loader
        self.model_name = load_detection_settings().get("detectionModel", "yolo11l.pt")
        # Lazy-load model to avoid heavy operations during import/startup
        self.model = None
        self.settings = load_detection_settings()
        self.capture: Optional[cv2.VideoCapture] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.frame_lock = threading.Lock()
        self.latest_frame = self._create_placeholder("Источник не настроен")
        self.active_clients = 0

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.running = True
        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if not self.thread:
            return
        self.running = False
        if self.capture:
            self.capture.release()
            self.capture = None
        self.thread.join(timeout=1)
        self.thread = None

    def restart(self) -> None:
        was_running = self.thread is not None and self.thread.is_alive()
        self.stop()
        if was_running or self.active_clients > 0:
            self.start()

    def update_settings(self, settings: Dict, restart: bool = True) -> None:
        self.settings = settings
        if restart:
            self.restart()

    def update_model(self, model_name: str, restart: bool = True) -> None:
        self.model_name = model_name
        # reset model so it will be loaded lazily on first inference
        self.model = None
        if restart:
            self.restart()

    def get_frame_bytes(self) -> bytes:
        with self.frame_lock:
            return self.latest_frame

    def stream(self) -> Iterator[bytes]:
        self.active_clients += 1
        self.start()
        try:
            while True:
                frame = self.get_frame_bytes()
                yield (
                    FRAME_BOUNDARY
                    + b"\r\nContent-Type: image/jpeg\r\n\r\n"
                    + frame
                    + b"\r\n"
                )
                time.sleep(0.05)
        finally:
            self.active_clients = max(0, self.active_clients - 1)
            if self.active_clients == 0:
                self.stop()

    def _process_loop(self) -> None:
        while self.running:
            try:
                if not self.capture or not self.capture.isOpened():
                    self.capture = self._open_capture()
                    if not self.capture or not self.capture.isOpened():
                        self._set_placeholder("Ожидание источника")
                        time.sleep(1)
                        continue

                ok, frame = self.capture.read()
                if not ok or frame is None:
                    if self.settings.get("sourceType") == "file" and self.capture:
                        self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else:
                        if self.capture:
                            self.capture.release()
                            self.capture = None
                        time.sleep(1)
                        continue

                processed = self._run_detection(frame)
                success, buffer = cv2.imencode(".jpg", processed)
                if success:
                    data = buffer.tobytes()
                    with self.frame_lock:
                        self.latest_frame = data
                else:
                    self._set_placeholder("Ошибка кодирования кадра")

            except Exception:
                self._set_placeholder("Ошибка обработки потока")
                if self.capture:
                    self.capture.release()
                    self.capture = None
                time.sleep(1)

    def _open_capture(self) -> Optional[cv2.VideoCapture]:
        source_type = self.settings.get("sourceType")
        if source_type == "rtsp" and self.settings.get("rtspUrl"):
            return cv2.VideoCapture(self.settings["rtspUrl"])
        if source_type == "file" and self.settings.get("videoFileName"):
            file_path = self.demo_dir / self.settings["videoFileName"]
            if file_path.exists():
                cap = cv2.VideoCapture(str(file_path))
                return cap
        return None

    def _run_detection(self, frame: np.ndarray) -> np.ndarray:
        # For demo files we skip YOLO processing to avoid heavy inference and
        # potential blocking/hangs. The widget will receive raw frames which
        # will be displayed (and the <video> fallback handles looping).
        if self.settings.get("sourceType") == "file":
            return frame

        target = self.settings.get("detectionTarget", "vehicles")
        classes = DETECTION_CLASS_MAP.get(target, [0])
        # load model lazily if needed
        if self.model is None:
            try:
                self.model = self.model_loader(self.model_name)
            except Exception:
                # if model cannot be loaded, return original frame
                return frame
        results = self.model(frame, classes=classes)
        annotated = results[0].plot()
        return annotated

    def _create_placeholder(self, text: str) -> bytes:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(
            frame,
            text,
            (20, 240),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        ok, buf = cv2.imencode(".jpg", frame)
        return buf.tobytes() if ok else b""

    def _set_placeholder(self, text: str) -> None:
        with self.frame_lock:
            self.latest_frame = self._create_placeholder(text)


