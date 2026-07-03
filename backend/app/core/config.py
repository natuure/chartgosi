from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/chartgosi"
    backend_cors_origins: str = "http://localhost:3000"
    supabase_url: str = ""
    supabase_jwt_secret: str = ""
    allow_dev_auth_fallback: bool = True
    openai_api_key: str = ""
    openai_model: str = "gpt-5.2"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        url = self.database_url.strip()
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)

        return url

    @property
    def asyncpg_connect_args(self) -> dict[str, int]:
        if self.uses_external_pooler:
            return {"statement_cache_size": 0}
        return {}

    @property
    def uses_external_pooler(self) -> bool:
        return "pooler.supabase.com" in self.database_url

    @property
    def normalized_supabase_url(self) -> str:
        return self.supabase_url.strip().rstrip("/")

    @property
    def supabase_issuer(self) -> str:
        if not self.normalized_supabase_url:
            return ""
        return f"{self.normalized_supabase_url}/auth/v1"

    @property
    def supabase_jwks_url(self) -> str:
        if not self.supabase_issuer:
            return ""
        return f"{self.supabase_issuer}/.well-known/jwks.json"


settings = Settings()
