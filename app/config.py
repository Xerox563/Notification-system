from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://notify:notify@localhost:5432/notify"
    redis_url: str = "redis://localhost:6379/0"

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    email_sender: str = "no-reply@notify.local"
    email_backup_sender: str = "backup@notify.local"

    sms_failure_rate: float = 0.0
    push_failure_rate: float = 0.0
    backup_failure_rate: float = 0.0

    max_attempts: int = 5
    backoff_base_seconds: float = 2.0
    backoff_cap_seconds: float = 300.0

    visibility_timeout_seconds: int = 60
    worker_concurrency: int = 5
    poll_interval_seconds: float = 0.5

    user_rate_capacity: int = 10
    user_rate_per_second: float = 1.0
    provider_rate_capacity: int = 200
    provider_rate_per_second: float = 100.0

    breaker_failure_threshold: int = 5
    breaker_recovery_seconds: float = 30.0

    idempotency_ttl_seconds: int = 86400
    bulk_chunk_size: int = 500
    bulk_max_users: int = 100000

    metrics_port: int = 0


@lru_cache
def get_settings() -> Settings:
    return Settings()
