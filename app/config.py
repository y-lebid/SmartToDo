from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "ToDo App"
    DB_URL: str = "sqlite:///./todo.db"
    JWT_SECRET: str = "supersecret"
    JWT_ALGORITHM: str = "HS256"

    class Config:
        env_file = ".env"

settings = Settings()
