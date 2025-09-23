from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Lease SaaS Backend"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    FRONTEND_ORIGIN: str = "http://localhost:8080"

    JWT_SECRET: str = "dev-secret"
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_MB_FREE: int = 100
    MAX_UPLOAD_MB_PRO: int = 5120
    MAX_FILE_SIZE_MB: int = 50

    STRIPE_API_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_ID_PRO: str = ""
    STRIPE_SUCCESS_URL: str = "http://localhost:8080/billing-success"
    STRIPE_CANCEL_URL: str = "http://localhost:8080/billing-cancel"

    DATABASE_URL: str = "sqlite:///./app.db"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
