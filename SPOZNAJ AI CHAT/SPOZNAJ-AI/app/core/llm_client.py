from openai import OpenAI
from app.core.config import Settings

_settings = Settings()


def get_llm_client() -> OpenAI:
    if not _settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY ni nastavljen v .env datoteki.")
    return OpenAI(api_key=_settings.openai_api_key)
