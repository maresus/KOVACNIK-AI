from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Nastavitve branja iz .env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignoriraj dodatne env spremenljivke
    )
    
    # Ime projekta (ni nujno v .env, ima default)
    project_name: str = Field(default="Kovačnik AI")
    
    # OpenAI ključ
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    
    # Database URL za PostgreSQL
    database_url: str | None = Field(default=None, alias="DATABASE_URL")

    # Chat engine rollout flags (v2|v3). v3 is prepared but not switched by default.
    chat_engine: str = Field(default="v2", alias="CHAT_ENGINE")
    intent_confidence_min: float = Field(default=0.85, alias="INTENT_CONFIDENCE_MIN")
    v3_shadow_mode: bool = Field(default=False, alias="V3_SHADOW_MODE")
    v3_intent_model: str = Field(default="gpt-4.1-mini", alias="V3_INTENT_MODEL")
