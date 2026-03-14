from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Knowledge-Driven Evaluation & Report System"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/paper"
    generated_papers_dir: str = "e:/paper/backend/generated_papers"
    generated_papers_mount_path: str = "/generated-papers"

    # Network proxy defaults required by the project environment.
    http_proxy: str = "http://127.0.0.1:7890"
    https_proxy: str = "https://127.0.0.1:7890"
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    llm_temperature: float = 0.35

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
