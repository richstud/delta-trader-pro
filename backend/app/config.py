from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str = ""
    SUPABASE_JWT_AUDIENCE: str = "authenticated"

    REDIS_URL: str = "redis://127.0.0.1:6379/3"
    ENCRYPTION_KEY: str

    DELTA_BASE_URL: str = "https://api.delta.exchange"
    DELTA_WS_URL: str = "wss://socket.delta.exchange"
    DELTA_SYMBOLS: str = "BTCUSD,ETHUSD"

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8010
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "*"

    @property
    def symbols(self) -> list[str]:
        return [s.strip().upper() for s in self.DELTA_SYMBOLS.split(",") if s.strip()]

    @property
    def cors_origins(self) -> list[str]:
        return [s.strip() for s in self.CORS_ORIGINS.split(",") if s.strip()]


settings = Settings()  # type: ignore[call-arg]
