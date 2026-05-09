from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Swing Backend"
    # Railway provides DATABASE_URL. We use psycopg2 as the driver.
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/swing_db"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
