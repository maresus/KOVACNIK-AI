from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Nastavitve branja iz .env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Ime projekta (ni nujno v .env, ima default)
    project_name: str = Field(default="Kovačnik AI")

    # OpenAI ključ – bere iz env spremenljivke OPENAI_API_KEY
    openai_api_key: str | None = Field(default=None, env="OPENAI_API_KEY")
