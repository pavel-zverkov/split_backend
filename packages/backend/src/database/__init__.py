from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from ..logger import logger

from ..config import Config

SQLALCHEMY_DATABASE_URL = f'postgresql://{Config.POSTGRES_USER}:' + \
                          f'{Config.POSTGRES_PASSWORD}@' + \
                          f'{Config.POSTGRES_HOST}:{Config.POSTGRES_PORT}' + \
                          f'/{Config.POSTGRES_DB}'


engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
