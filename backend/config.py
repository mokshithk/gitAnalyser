import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "cp_user"
    DB_PASSWORD: str = ""
    DB_NAME: str = "codeprovenance"
    DATABASE_URL: str = "mysql+pymysql://cp_user:CP_Sec2026!Prove_MariaDB%239@127.0.0.1:3306/codeprovenance?charset=utf8mb4"

    SECRET_KEY: str = "supersecretkey_change_me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    MAX_REPO_SIZE_MB: int = 250
    MAX_ZIP_SIZE_MB: int = 50
    CLONE_TIMEOUT_SECONDS: int = 60
    RETENTION_DAYS: int = 30
    SCANS_PER_USER_PER_HOUR: int = 20

    WORKDIR: str = str(BASE_DIR / "workdir")

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
