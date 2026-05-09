from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Swing Backend"
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/swing_db"

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        # Railway provides 'postgres://', but SQLAlchemy requires 'postgresql://'
        # Also ensure we use the psycopg2 driver
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
