import os
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(BASE_DIR)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[
            os.path.join(ROOT_DIR, ".env"),
            os.path.join(BASE_DIR, ".env"),
        ],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Enterprise AI Sales CRM"
    APP_URL: str = "http://localhost:5173"
    DATABASE_URL: str = "postgres://postgres:postgres@localhost:5432/crm_ai"
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET: str = "change-me-in-production"
    JWT_EXPIRE_DAYS: int = 7

    # LLM
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIM: int = 1536

    # Storage
    UPLOAD_DIR: str = os.path.join(ROOT_DIR, "uploads")

    # SMTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = ""


settings = Settings()
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
