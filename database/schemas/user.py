from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: int
    email: EmailStr
    password: str

    class Config:
        from_attributes = True

class AuthRequest(BaseModel):
    email: EmailStr
    password: str