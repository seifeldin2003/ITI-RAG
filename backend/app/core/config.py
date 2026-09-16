"""Settings loaded from environment / .env -- see .env.example for the
full list. Nothing here is hard-coded that should vary between machines
(the doc explicitly calls out hard-coded localhost URLs as a common
mistake -- same principle applies to paths and model names)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Where the notebook (Phase 2.7) persisted the Chroma vector store + config.json
    vector_store_dir: str = "data/vector_store"
    vector_store_collection: str = "automotive_diagnostics"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    ollama_model: str = "llama3.2:3b"
    ollama_base_url: str = "http://localhost:11434"

    # Frontend origin(s) allowed to call this API -- CORS
    cors_allow_origins: str = "http://localhost:8501"

    retrieval_k: int = 4


settings = Settings()
