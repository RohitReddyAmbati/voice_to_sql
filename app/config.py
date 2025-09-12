from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://reader:NWDMCE5xdipIjRrp@hh-pgsql-public.ebi.ac.uk:5432/pfmegrnargs?sslmode=require"
    OLLAMA_MODEL: str = "llama3.1:8b"
    TEMPERATURE: float = 0.0
    DEFAULT_LIMIT: int = 200
    MAX_ROWS: int = 5000
    TIMEOUT_S: int = 10
    SCHEMA_MAX_TABLES: int = 50      # cap how much schema we print
    SCHEMA_MAX_COLS_PER_TABLE: int = 30

    class Config:
        env_file = ".env"

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
