import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Settings
    PORT: int = 8000
    HOST: str = "127.0.0.1"
    SECRET_KEY: str = "prime_development_secret_key_change_me_in_production"
    
    # Database Settings
    DATABASE_URL: str = "sqlite:///./prime.db"
    
    # LLM Keys
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # Ollama Settings
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    
    # Workspace Directory
    PRIME_WORKSPACE_PATH: str = os.path.join(
        os.path.expanduser("~"), ".gemini", "antigravity-ide", "scratch", "prime-workspace"
    )

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
