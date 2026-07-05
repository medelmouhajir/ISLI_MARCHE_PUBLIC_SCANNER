from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "isli-core"

    CACHE_TTL_SECONDS: int = 300
    REQUEST_DELAY_MS: int = 750
    MAX_CONCURRENT_PAGES: int = 1
    DEFAULT_MAX_PAGES_SCAN: int = 5
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    PORTAL_BASE_URL: str = "https://www.marchespublics.gov.ma"
    USER_AGENT: str = (
        "ISLI-Maroc-Marches-Publics-Scanner/1.0 "
        "(+https://github.com/medelmouhajir/isli-skills-registry)"
    )

    LOG_LEVEL: str = "info"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
