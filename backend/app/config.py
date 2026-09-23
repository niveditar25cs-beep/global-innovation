import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Transformer Failure Risk Monitoring System"
    APP_ENV: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_PREFIX: str = "/api"
    API_V1_STR: str = "/api/v1"
    CORS_ORIGINS: str = "*"
    CORS_ALLOW_CREDENTIALS: bool = True
    ENABLE_SECURITY_HEADERS: bool = True
    STRICT_TRANSPORT_SECURITY: bool = False
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/transformer_db"
    SAMPLE_DATASET_PATH: str = "./data/sample_transformer_data.csv"
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 20
    REDIS_SOCKET_TIMEOUT: float = 1.5
    REDIS_SOCKET_CONNECT_TIMEOUT: float = 1.5
    REDIS_CURSOR_TTL_SECONDS: int = 14400  # 4 hours
    REDIS_CACHE_TTL_SECONDS: int = 60  # 1 minute default cache
    REDIS_RATE_LIMIT_ENABLED: bool = True
    REDIS_RATE_LIMIT_REQUESTS: int = 100  # requests per window
    REDIS_RATE_LIMIT_WINDOW_SECONDS: int = 60  # 1 minute window

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def resolved_async_database_url(self) -> str:
        """Returns the asyncpg database URL for async operations."""
        url = self.DATABASE_URL.strip()
        if url.startswith("sqlite+aiosqlite:///./"):
            rel_path = url.replace("sqlite+aiosqlite:///./", "")
            base_dir = Path(__file__).resolve().parent.parent
            full_path = base_dir / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite+aiosqlite:///{full_path.as_posix()}"
        if url.startswith("sqlite:///"):
            return url.replace("sqlite:///", "sqlite+aiosqlite:///")
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    @property
    def resolved_sync_database_url(self) -> str:
        """Returns the sync database URL for migrations or sync operations."""
        url = self.DATABASE_URL.strip()
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql://", 1)
        if url.startswith("sqlite+aiosqlite:///"):
            return url.replace("sqlite+aiosqlite:///", "sqlite:///", 1)
        if url.startswith("sqlite:///./"):
            rel_path = url.replace("sqlite:///./", "")
            base_dir = Path(__file__).resolve().parent.parent
            full_path = base_dir / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{full_path.as_posix()}"
        return url

    @property
    def resolved_database_url(self) -> str:
        return self.resolved_sync_database_url

    @property
    def resolved_sample_dataset_path(self) -> Path:
        base_dir = Path(__file__).resolve().parent.parent
        if self.SAMPLE_DATASET_PATH.startswith("./"):
            return base_dir / self.SAMPLE_DATASET_PATH[2:]
        return Path(self.SAMPLE_DATASET_PATH)

    @property
    def masked_database_url(self) -> str:
        """Safe connection string representation for logs with credentials redacted."""
        from app.utils.sanitizer import mask_connection_string

        return mask_connection_string(self.DATABASE_URL)

    @property
    def masked_redis_url(self) -> str:
        """Safe Redis URL representation with credentials redacted."""
        from app.utils.sanitizer import mask_connection_string

        return mask_connection_string(self.REDIS_URL)


settings = Settings()
