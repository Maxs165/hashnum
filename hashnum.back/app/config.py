from pydantic import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    JWT_ALG: str = os.getenv("JWT_ALG", "HS256")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me")
    JWT_PRIVATE_KEY: Optional[str] = os.getenv("JWT_PRIVATE_KEY")
    JWT_PUBLIC_KEY: Optional[str] = os.getenv("JWT_PUBLIC_KEY")
    JWT_ISSUER: str = os.getenv("JWT_ISSUER", "cracknum")
    JWT_AUDIENCE: str = os.getenv("JWT_AUDIENCE", "cracknum-clients")
    ACCESS_TTL_S: int = int(os.getenv("ACCESS_TTL_S", "3600"))
    REFRESH_TTL_S: int = int(os.getenv("REFRESH_TTL_S", str(24 * 3600)))
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    COOKIE_DOMAIN: str | None = os.getenv("COOKIE_DOMAIN") or None

    ADMIN_USER: str = os.getenv("ADMIN_USER", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin")

    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "http://localhost:8080").split(",")


settings = Settings()
