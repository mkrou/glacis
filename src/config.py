from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    flight_api_token: str
    openai_api_key: str
    port: int = 8000


settings = Settings()  # type: ignore[call-arg]
