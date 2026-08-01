from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = 'postgresql+psycopg2://postgres:Yuen311005@127.0.0.1:5432/health_assistant'
    jwt_secret_key: str = 'MY_SUPER_SECRET_KEY'
    jwt_algorithm: str = 'HS256'
    jwt_expire_minutes: int = 60 * 24

    class Config:
        env_file = '.env'

settings = Settings()