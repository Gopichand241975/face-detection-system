"""Application configuration via environment variables."""

from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://faceuser:facepass@db:5432/facedetection"

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://frontend:3000", "http://localhost"]

    # Face detection confidence threshold
    FACE_CONFIDENCE_THRESHOLD: float = 0.5

    # Max ROI records to return in list endpoint
    ROI_PAGE_SIZE: int = 100

    # Secret key for any token signing
    SECRET_KEY: str = "change-me-in-production"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
