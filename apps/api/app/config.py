from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://floodlens:change-me-locally@db:5432/floodlens"
    log_level: str = "INFO"
    web_origin: str = "http://localhost:8000"
    terrain_dir: str = "/imports/fabdem"
    terrain_dataset_version: str = "FABDEM user-mounted local tiles"
    terrain_resolution_m: float = 30.0
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
