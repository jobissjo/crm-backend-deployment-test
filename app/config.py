from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    jwt_secret: str = Field(min_length=32)
    access_token_minutes: int = Field(default=60, ge=1, le=1440)

    @field_validator("database_url")
    @classmethod
    def async_postgres_only(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use postgresql+asyncpg://")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
