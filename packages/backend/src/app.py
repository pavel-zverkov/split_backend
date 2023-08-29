from fastapi import FastAPI

from .competition.competition_contoller import competition_router
from .database import (Base,
                       engine,
                       tables)
from .event.event_controller import event_router
from .user.user_controller import user_router
from .workout.workout_controller import workout_router

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(user_router)
app.include_router(workout_router)
app.include_router(competition_router)
app.include_router(event_router)


@app.get("/")
async def root():
    return 'Hello! This is Split App API!'
