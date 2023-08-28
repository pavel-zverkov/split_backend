from fastapi import FastAPI

from .database import (Base,
                       SessionLocal,
                       engine,
                       tables)

Base.metadata.create_all(bind=engine)

app = FastAPI()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
