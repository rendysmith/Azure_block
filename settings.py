from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class ContentUnderstandingSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="CONTENT_UNDERSTANDING_",
    )

    endpoint: str = Field(
        default="https://dev-inwa.services.ai.azure.com/",
        description="Endpoint Content Understanding (например https://<your-resource>.services.ai.azure.com/)"
    )
    key: str = Field(default="", description="API Key")
    api_version: str = Field(default="2025-11-01", description="API version")