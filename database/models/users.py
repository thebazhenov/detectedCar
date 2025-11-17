from datetime import datetime
from sqlalchemy import String, text, Column
from sqlalchemy.orm import Mapped, mapped_column
from database.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(250))
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
