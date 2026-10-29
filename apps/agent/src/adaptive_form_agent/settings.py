from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="FORM_GUIDE_",
        extra="ignore",
    )

    supervisor_model: str = "openai:gpt-5.4"
    domain_model: str = "openai:gpt-5.4-mini"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"


settings = Settings()
