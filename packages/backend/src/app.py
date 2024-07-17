from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .competition.competition_contoller import competition_router
from .database import (Base,
                       engine,
                       tables)
from .event.event_controller import event_router
from .split_comparer.split_comparer_controller import split_comparer_router
from .user.user_controller import user_router
from .workout.workout_controller import workout_router
from .artifact.artifact_controller import artifact_router

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(user_router)
app.include_router(workout_router)
app.include_router(competition_router)
app.include_router(event_router)
app.include_router(split_comparer_router)
app.include_router(artifact_router)

app.mount("/css", StaticFiles(directory="frontend/css"), name="css")
app.mount("/java_script", StaticFiles(directory="frontend/java_script"),
          name="java_script")


@app.get("/")
async def root():
    return 'Hello! This is Split App API!'
