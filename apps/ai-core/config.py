from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    ANTHROPIC_API_KEY: str
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Mentor Settings
    ENABLE_DAILY_DIGEST: bool = True
    DAILY_DIGEST_HOUR: int = 7  # 7 AM
    DAILY_DIGEST_MINUTE: int = 0

    # Scheduler Settings
    ENABLE_SCHEDULER: bool = True

    # Cron API Key for external trigger
    CRON_API_KEY: str = "change-me-in-production"

    class Config:
        env_file = ".env"


settings = Settings()
