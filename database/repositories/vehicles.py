from typing import Sequence
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Vehicle
from database.schemas import VehicleCreate, VehicleUpdate


class VehicleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: VehicleCreate) -> Vehicle:
        vehicle = Vehicle(
            license_plate=data.license_plate,
            owner_name=data.owner_name,
            notes=data.notes,
            is_active=data.is_active,
        )
        self.session.add(vehicle)
        await self.session.flush()
        return vehicle

    async def get(self, vehicle_id: int) -> Vehicle | None:
        return await self.session.get(Vehicle, vehicle_id)

    async def get_by_plate(self, license_plate: str) -> Vehicle | None:
        res = await self.session.execute(
            select(Vehicle).where(Vehicle.license_plate == license_plate)
        )
        return res.scalar_one_or_none()

    async def list(self, limit: int = 100, offset: int = 0, active_only: bool = False) -> Sequence[Vehicle]:
        query = select(Vehicle)
        if active_only:
            query = query.where(Vehicle.is_active == True)
        query = query.order_by(Vehicle.created_at.desc()).limit(limit).offset(offset)
        res = await self.session.execute(query)
        return res.scalars().all()

    async def get_active_plates(self):
        """Получить список активных номеров для проверки доступа"""
        res = await self.session.execute(
            select(Vehicle.license_plate).where(Vehicle.is_active == True)
        )
        return [plate for plate in res.scalars().all()]

    async def update(self, vehicle_id: int, data: VehicleUpdate) -> Vehicle | None:
        vehicle = await self.get(vehicle_id)
        if not vehicle:
            return None
        
        if data.license_plate is not None:
            vehicle.license_plate = data.license_plate
        if data.owner_name is not None:
            vehicle.owner_name = data.owner_name
        if data.notes is not None:
            vehicle.notes = data.notes
        if data.is_active is not None:
            vehicle.is_active = data.is_active
        
        await self.session.flush()
        return vehicle

    async def delete(self, vehicle_id: int) -> int:
        res = await self.session.execute(delete(Vehicle).where(Vehicle.id == vehicle_id))
        return res.rowcount or 0

