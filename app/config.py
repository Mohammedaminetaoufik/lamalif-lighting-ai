from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = Field("smart-lighting-ai", alias="APP_NAME")
    port: int = Field(8090, alias="PORT")

    database_url: str = Field(..., alias="DATABASE_URL")
    log_database_url: str | None = Field(None, alias="LOG_DATABASE_URL")

    llm_provider: str = Field("groq", alias="LLM_PROVIDER")

    openai_api_key: str | None = Field(None, alias="OPENAI_API_KEY")

    groq_api_key: str | None = Field(None, alias="GROQ_API_KEY")
    groq_model: str = Field("llama-3.3-70b-versatile", alias="GROQ_MODEL")

    max_rows: int = Field(500, alias="MAX_ROWS")
    default_limit: int = Field(100, alias="DEFAULT_LIMIT")
    sql_timeout_seconds: int = Field(5, alias="SQL_TIMEOUT_SECONDS")

    allowed_views: str = Field(
        "ai_lampadaire_status,ai_lcu_status,ai_open_alerts,ai_workorders,ai_telemetry_latest",
        alias="ALLOWED_VIEWS",
    )

    # ── RAG Configuration ──────────────────────────────────────
    rag_enabled: bool = Field(True, alias="RAG_ENABLED")
    rag_backend: str = Field("pgvector", alias="RAG_BACKEND")
    rag_top_k: int = Field(5, alias="RAG_TOP_K")
    rag_max_context_chars: int = Field(6000, alias="RAG_MAX_CONTEXT_CHARS")
    rag_chunk_size: int = Field(1000, alias="RAG_CHUNK_SIZE")
    rag_chunk_overlap: int = Field(150, alias="RAG_CHUNK_OVERLAP")
    embedding_model: str = Field(
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        alias="EMBEDDING_MODEL",
    )
    embedding_dimension: int = Field(384, alias="EMBEDDING_DIMENSION")

    @property
    def allowed_views_list(self) -> list[str]:
        return [view.strip() for view in self.allowed_views.split(",") if view.strip()]

    @property
    def effective_log_database_url(self) -> str:
        return self.log_database_url or self.database_url

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
