from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    SESSION_TTL_S: int = int(os.getenv("SESSION_TTL_S", str(7 * 24 * 3600)))  # 7d
    COOKIE_DOMAIN: Optional[str] = os.getenv("COOKIE_DOMAIN")
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "true").lower() == "true"
    COOKIE_SAMESITE: str = os.getenv("COOKIE_SAMESITE", "lax")

    ADMIN_USER: str = os.getenv("ADMIN_USER", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin")

    CORS_ORIGINS: List[str] = [
        s.strip()
        for s in os.getenv("CORS_ORIGINS", "http://localhost:8080").split(",")
        if s.strip()
    ]


settings = Settings()
