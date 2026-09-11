"""Alembic env — lê a URL de app/database.py e usa os models como fonte de schema."""
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# 1) Garante que a raiz do projeto esteja no sys.path (permite `from app...`)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# 2) ÚNICA fonte de verdade da URL (lê DATABASE_URL do ambiente, fallback SQLite)
from app.database import DATABASE_URL

# 3) Importar os models REGISTRA as 11 tabelas no Base.metadata
from app.models import Base  # noqa: F401

config = context.config

# 4) A URL real substitui o placeholder do alembic.ini
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Modo offline: gera SQL sem conectar (--sql)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            # Essencial p/ SQLite (ALTER TABLE limitado); inócuo no PostgreSQL:
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()