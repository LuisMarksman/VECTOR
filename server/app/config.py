"""Central configuration for the VECTOR server.

All settings are read from environment variables (see the repository-root
``.env.example``). Nothing is hard-coded so the same image can run in
development, in Docker and on the target hardware.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, populated from the environment."""

    model_config = SettingsConfigDict(
        env_prefix="VECTOR_",
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- General ---------------------------------------------------------
    env: str = "development"
    log_level: str = "info"

    # --- HTTP server -----------------------------------------------------
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # --- Language model --------------------------------------------------
    llm_provider: str = "mock"  # mock | anthropic | openai | local
    llm_model: str = "claude-sonnet-4-5"

    # --- Persistence -----------------------------------------------------
    memory_backend: str = "sqlite"
    db_url: str = "sqlite:///./data/vector.db"

    # --- MQTT bus --------------------------------------------------------
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_base_topic: str = "vector"

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""
    return Settings()
