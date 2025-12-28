from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field


class Settings(BaseSettings):
    # App Config
    PROJECT_NAME: str = "FactoryOS"
    ENVIRONMENT: Literal["dev", "prod"] = "dev"

    # Database Settings
    POSTGRES_USER: str = "factory_user"
    POSTGRES_PASSWORD: str = "factory_password"
    POSTGRES_DB: str = "factory_db"
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: str = "5432"
    DATABASE_URL: str | None = None

    @computed_field
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """Returns the PostgreSQL connection string if DATABASE_URL is not set."""
        if self.DATABASE_URL:
            # Ensure it uses the asyncpg driver if it's a PG URL
            if self.DATABASE_URL.startswith("postgresql://"):
                return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
            return self.DATABASE_URL
        
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # eBay API Credentials
    EBAY_APP_ID: str | None = None
    EBAY_CERT_ID: str | None = None
    EBAY_RU_NAME: str | None = None
    EBAY_REFRESH_TOKEN: str | None = None
    
    # eBay Environment Toggle
    EBAY_API_ENV: Literal["SANDBOX", "PRODUCTION"] = "SANDBOX"

    @computed_field
    @property
    def EBAY_API_BASE_URL(self) -> str:
        """Returns the correct eBay API base URL based on the environment."""
        if self.EBAY_API_ENV == "PRODUCTION":
            return "https://api.ebay.com"
        return "https://api.sandbox.ebay.com"

    @computed_field
    @property
    def EBAY_AUTH_URL(self) -> str:
        """Returns the correct eBay OAuth authorization URL based on the environment."""
        if self.EBAY_API_ENV == "PRODUCTION":
            return "https://auth.ebay.com/oauth2/authorize"
        return "https://auth.sandbox.ebay.com/oauth2/authorize"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Globally accessible settings instance
settings = Settings()
