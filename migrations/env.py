from __future__ import with_statement

import logging
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from flask import current_app

config = context.config

logger = logging.getLogger('alembic.env')

project_root = Path(__file__).resolve().parent.parent
config_path = Path(config.config_file_name) if config.config_file_name else None
if not config_path or not config_path.is_file():
    config_path = project_root / "alembic.ini"
    if config_path.is_file():
        config.config_file_name = str(config_path)
    else:
        config_path = None

if config_path and config_path.is_file():
    fileConfig(config_path)
else:
    logger.warning("Alembic config file not found at %s", config_path or "unknown")

try:
    target_metadata = current_app.extensions['migrate'].db.metadata
except Exception as exc:  # pragma: no cover
    target_metadata = None
    logger.error("Failed to load target metadata: %s", exc)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = str(current_app.extensions['migrate'].db.engine.url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = current_app.extensions['migrate'].db.engine

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


def run_migrations() -> None:
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()


run_migrations()
