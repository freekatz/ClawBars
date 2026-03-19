from __future__ import annotations

import logging
import sys
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_DEFAULTS = {"change-me", "change-me-too", "admin123456"}
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(
        default="postgresql+asyncpg://clawbars:secret@localhost:5432/clawbars",
        alias="DATABASE_URL",
    )
    admin_api_key: str = Field(default="change-me", alias="ADMIN_API_KEY")
    secret_key: str = Field(default="change-me-too", alias="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=10080, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=30, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="info", alias="LOG_LEVEL")
    log_dir: str = Field(default="", alias="LOG_DIR")
    log_max_bytes: int = Field(default=10 * 1024 * 1024, alias="LOG_MAX_BYTES")
    log_backup_count: int = Field(default=5, alias="LOG_BACKUP_COUNT")
    workers: int = Field(default=1, alias="WORKERS")

    # Initial admin seed
    init_admin_email: str = Field(default="admin@clawbars.local", alias="INIT_ADMIN_EMAIL")
    init_admin_password: str = Field(default="admin123456", alias="INIT_ADMIN_PASSWORD")
    init_admin_name: str = Field(default="ClawBars Admin", alias="INIT_ADMIN_NAME")

    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        alias="CORS_ORIGINS",
    )

    @model_validator(mode="after")
    def _check_insecure_defaults(self) -> Settings:
        if self.debug:
            return self
        # Hard block: cryptographic keys MUST be changed in production
        insecure: list[str] = []
        if self.secret_key in _INSECURE_DEFAULTS:
            insecure.append("SECRET_KEY")
        if self.admin_api_key in _INSECURE_DEFAULTS:
            insecure.append("ADMIN_API_KEY")
        if insecure:
            msg = (
                f"SECURITY: The following settings still use insecure default values: "
                f"{', '.join(insecure)}. Set them via environment variables or .env file. "
                f"Set DEBUG=true to bypass this check in development."
            )
            logger.critical(msg)
            sys.exit(1)
        # Soft warning: seed password is only used on first boot
        if self.init_admin_password in _INSECURE_DEFAULTS:
            logger.warning(
                "INIT_ADMIN_PASSWORD uses an insecure default value. "
                "Change it before deploying to production."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
