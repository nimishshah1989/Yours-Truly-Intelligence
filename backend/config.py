"""Application configuration loaded from environment variables."""

from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = ""
    database_url_readonly: str = ""

    # Claude AI
    anthropic_api_key: str = ""

    # Email notifications
    resend_api_key: str = ""
    notify_emails: str = ""

    # PetPooja POS — Orders API
    petpooja_app_key: str = ""
    petpooja_app_secret: str = ""
    petpooja_access_token: str = ""
    petpooja_restaurant_id: str = ""
    petpooja_base_url: str = "https://api.petpooja.com/v2"

    # PetPooja Menu API (separate credentials from Orders API)
    petpooja_menu_app_key: str = ""
    petpooja_menu_app_secret: str = ""
    petpooja_menu_access_token: str = ""
    # menuSharingCode = RestID — e.g. "34cn0ieb1f" for YoursTruly
    petpooja_rest_id: str = ""
    # Full cookie value: "PETPOOJA_API=..."
    petpooja_cookie: str = ""

    # Tally
    tally_upload_dir: str = "/tmp/tally_uploads"

    # Email
    resend_from_email: str = "alerts@yourstruly.in"

    # Auth
    api_key: str = ""  # Set to enable API key auth; empty = disabled

    # Rate limiting
    rate_limit_per_minute: int = 120  # requests per minute per IP

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
