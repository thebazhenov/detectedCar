from contextlib import asynccontextmanager
from .db import SessionLocal
from .repositories import UserRepository, VehicleRepository

class UnitOfWork:
    def __init__(self):
        self.session = SessionLocal()
        self.users = UserRepository(self.session)
        self.vehicles = VehicleRepository(self.session)

    @asynccontextmanager
    async def __call__(self):
        try:
            yield self
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        finally:
            await self.session.close()