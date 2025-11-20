from typing import Sequence
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User
from database.schemas import UserCreate
from database.security import hash_password, verify_password

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: UserCreate) -> User:
        hashed = hash_password(data.password)
        user = User(email=data.email, password=hashed, role=data.role or "operator")
        self.session.add(user)
        await self.session.flush()
        return user

    async def get(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def by_email(self, email: str) -> User | None:
        res = await self.session.execute(select(User).where(User.email == email))
        return res.scalar_one_or_none()

    async def check_credentials(self, email: str, password: str) -> User | None:
        """Возвращает пользователя, если пароль верный"""
        user = await self.by_email(email)
        if not user:
            return None
        if verify_password(password, user.password):
            return user
        return None

    async def list(self, limit: int = 50, offset: int = 0) -> Sequence[User]:
        res = await self.session.execute(select(User).limit(limit).offset(offset))
        return res.scalars().all()

    async def delete(self, user_id: int) -> int:
        res = await self.session.execute(delete(User).where(User.id == user_id))
        return res.rowcount or 0
