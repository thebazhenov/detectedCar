from optparse import Option
from typing import List, Optional
from pydantic import BaseModel
from fastapi import UploadFile


class StartDetectionYolo(BaseModel):
    source: int
    camera_id: str
    function_name: str
    skip_frames: int

class ImageData(BaseModel):
    title: str              # Название изображения
    description: str | None # Описание (необязательно)
    file: UploadFile        # Файл изображения


class StopDetectionYolo(BaseModel):
    camera_id: str

