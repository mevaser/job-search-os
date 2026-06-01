from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Job Search OS API"
    database_url: str = "sqlite:///./jobsearchos.db"

    class Config:
        env_file = ".env"

settings = Settings()
