from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from .config import settings

engine: Engine = create_engine(settings.database_url, pool_pre_ping=True)


def healthcheck() -> bool:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True
