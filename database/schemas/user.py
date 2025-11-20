from typing import Literal
from pydantic import BaseModel, EmailStr

UserRole = Literal["admin", "operator"]


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: UserRole = "operator"


class UserRead(BaseModel):
    id: int
    email: EmailStr
    role: UserRole

    class Config:
        from_attributes = True

class AuthRequest(BaseModel):
    email: EmailStr
    password: str