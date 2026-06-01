from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Job Search OS API"
    database_url: str = "sqlite:///./jobsearchos.db"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
