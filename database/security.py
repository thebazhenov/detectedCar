from passlib.context import CryptContext

# Argon2id — самый безопасный вариант
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__memory_cost=102400,  # 100 MB RAM
    argon2__time_cost=2,         # 2 iterations
    argon2__parallelism=8,       # 8 threads
)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)