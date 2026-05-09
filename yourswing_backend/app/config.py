from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Swing Backend"
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/swing_db"

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        # Railway provides 'postgres://', but SQLAlchemy requires 'postgresql://'
        # We also force the use of the driver to avoid ambiguity
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        
        # If the URL doesn't specify a driver, add it based on what's available
        # Most Railway/Neon setups work best with psycopg2 or the direct postgresql driver
        if "postgresql://" in url and "+psycopg" not in url:
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
            
        return url

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
