from pydantic import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Proposta Suite API"
    API_PREFIX: str = "/api"
    DB_URL: str = "sqlite+aiosqlite:///./proposta.db"
    SMTP_HOST: str = "smtp.exemplo.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "no-reply@exemplo.com"
    SMTP_PASS: str = "SENHA_SUPER_SECRETA"
    ENV: str = "dev"

    class Config:
        env_file = ".env"


settings = Settings()
