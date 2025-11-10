from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="app_db", alias="DB_NAME")
    db_user: str = Field(default="app", alias="DB_USER")
    db_pass: str = Field(default="secret", alias="DB_PASS")

    @property
    def sync_dsn(self) -> str:
        return f"postgresql+psycopg://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def async_dsn(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"

    class Config:
        env_file = ".env"

settings = Settings()