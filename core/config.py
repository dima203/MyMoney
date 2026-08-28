from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DEBUG: bool = False

    BACKEND_URL: str = Field(default="http://localhost:8000")
    BACKEND_TRUST_PROXY: bool = False

    GOOGLE_OAUTH_CLIENT_ID: str = ""


SETTINGS = Settings()
