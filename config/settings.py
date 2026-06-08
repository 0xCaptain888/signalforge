"""Runtime settings loaded from .env (pydantic-settings)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cmc_api_key: str = ""
    cmc_base_url: str = "https://pro-api.coinmarketcap.com"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    request_timeout: int = 30
    max_retries: int = 5
    rate_limit_per_min: int = 28

    cache_dir: str = "data/raw"
    sample_dir: str = "data/raw/_samples"
    processed_dir: str = "data/processed"
    outputs_dir: str = "outputs"

    seed: int = 42


settings = Settings()
