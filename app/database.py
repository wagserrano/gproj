import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Dev: SQLite | Produção futura: basta trocar a variável de ambiente
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./app-gproj.db",
    # "postgresql+psycopg://user:senha@localhost:5432/nucleo",
)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    """Dependency do FastAPI: abre/fecha a sessão por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()