
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from pydantic_settings import BaseSettings, SettingsConfigDict

from collections.abc import Generator
from sqlalchemy.orm import Session

class Settings(BaseSettings):
    DATABASE_URL: str
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4.1-mini"

    JWT_SECRET_KEY: str
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    COOKIE_SECURE: bool = False

    RESEND_API_KEY: str | None = None
    EMAIL_FROM: str = "FlexTech CareerOS <onboarding@resend.dev>"
    FRONTEND_URL: str = "http://localhost:5173"
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()