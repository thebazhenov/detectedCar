from datetime import datetime
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from database.db import Base


class Plate(Base):
    __tablename__ = "plates"

    id: Mapped[int] = mapped_column(primary_key=True)
    client: Mapped[int] = mapped_column(primary_key=True)
    plate: Mapped[str] = mapped_column(String(250))
