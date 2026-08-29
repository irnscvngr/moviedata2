from pydantic import PostgresDsn, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # LETTERBOXD CREDENTIALS
    LETTERBOXD_USERNAME: str
    LETTERBOXD_PASSWORD: str

    # TMDB CREDENTIALS
    TMDB_API_KEY: str

    # DATABASE CREDENTIALS
    POSTGRES_PASSWORD: str
    POSTGRES_USER: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "moviedata"

    @property
    def database_url(self) -> str:
        """Constructs a standard SQLAlchemy connection URI."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Tell Pydantic to read from a local .env file
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"  # Prevents crashing if extra env vars exist
    )

# Instantiate as a singleton to use across your app
settings = Settings()