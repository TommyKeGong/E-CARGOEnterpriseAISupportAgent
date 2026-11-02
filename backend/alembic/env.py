from os import environ

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.models import Base

config = context.config
target_metadata = Base.metadata


def run_migrations_online() -> None:
    settings = config.get_section(config.config_ini_section, {})
    settings["sqlalchemy.url"] = environ["DATABASE_URL"]
    engine = engine_from_config(settings, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
