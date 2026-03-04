from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # FastAPI
    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Database
    DATABASE_URL: str

    # Qdrant
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "devpunks_knowledge"

    # LLM
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    LLM_PROVIDER: str = "anthropic"

    # Embeddings
    EMBEDDING_PROVIDER: str = "openai"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Voice
    VAPI_API_KEY: Optional[str] = None
    VAPI_WEBHOOK_SECRET: Optional[str] = None
    ELEVENLABS_API_KEY: Optional[str] = None
    ELEVENLABS_VOICE_ID: Optional[str] = None
    ELEVENLABS_MODEL: str = "eleven_multilingual_v2"
    ELEVENLABS_STABILITY: float = 0.5
    ELEVENLABS_SIMILARITY_BOOST: float = 0.8
    ELEVENLABS_STYLE: float = 0.6

    # SuperAdmin seed
    SUPERADMIN_EMAIL: str = "admin@devpunks.io"
    SUPERADMIN_PASSWORD: str = "change-me"

    # CORS
    ALLOWED_ORIGINS: str = "https://devpunks.io,https://admin.devpunks.io"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
