from pydantic import BaseModel


class StartDetectionYolo(BaseModel):
    source: int
    camera_id: str
    function_name: str
    skip_frames: int


class StopDetectionYolo(BaseModel):
    camera_id: str

