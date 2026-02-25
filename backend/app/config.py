from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AI Real Estate Assistant"
    debug: bool = False
    api_prefix: str = "/api/v1"

    database_url: str = "sqlite:///./real_estate.db"

    llm_provider: Literal["claude", "openai"] = "claude"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    llm_temperature: float = 0.1

    # Resend email
    resend_api_key: str = ""
    email_from: str = "Harry <onboarding@resend.dev>"

    upload_dir: str = "./uploads"
    max_file_size_mb: int = 10
    allowed_extensions: str = ".txt,.pdf,.docx,.doc"
    cors_origins: str = "http://localhost:5173"

    # Zillow API (RapidAPI)
    rapidapi_key: str = ""
    rapidapi_zillow_host: str = "real-estate101.p.rapidapi.com"

    # Twilio WhatsApp
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_number: str = ""  # e.g. whatsapp:+14155238886

    model_config = {"env_file": ".env"}


settings = Settings()
