import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv(override=False)  # Docker Compose env vars têm prioridade sobre o .env

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://nfextractor_user:Z0BgVLASZoNzQJev1RC1SZpMZkUan1DP@dpg-d8pv1ni8qa3s73c7qm10-a.oregon-postgres.render.com/nfextractor",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
