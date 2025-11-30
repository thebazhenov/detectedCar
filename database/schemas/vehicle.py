from pydantic import BaseModel
from datetime import datetime


class VehicleCreate(BaseModel):
    license_plate: str
    owner_name: str
    notes: str | None = None
    is_active: bool = True


class VehicleRead(BaseModel):
    id: int
    license_plate: str
    owner_name: str
    notes: str | None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class VehicleUpdate(BaseModel):
    license_plate: str | None = None
    owner_name: str | None = None
    notes: str | None = None
    is_active: bool | None = None

