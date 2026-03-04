"""Application configuration loaded from environment variables."""

from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://ytip_app:password@localhost:5432/ytip"
    database_url_readonly: str = ""

    # Claude AI
    anthropic_api_key: str = ""

    # Email notifications
    resend_api_key: str = ""
    notify_emails: str = ""

    # PetPooja POS
    petpooja_app_key: str = ""
    petpooja_app_secret: str = ""
    petpooja_access_token: str = ""
    petpooja_restaurant_id: str = ""
    petpooja_base_url: str = "https://api.petpooja.com/v2"

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    @property
    def readonly_url(self) -> str:
        """Read-only DB URL, falls back to main DATABASE_URL."""
        return self.database_url_readonly or self.database_url

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def notification_email_list(self) -> List[str]:
        if not self.notify_emails:
            return []
        return [email.strip() for email in self.notify_emails.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
