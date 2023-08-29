from fastapi import (APIRouter,
                     Depends,
                     HTTPException)
from sqlalchemy.orm import Session

from ..competition.competition_crud import get_competition
from ..database import get_db
from ..relations.user_competition_relation_crud import create_user_competition_relation
from ..relations.user_event_relation_crud import create_user_event_relation
from . import workout_crud
from .workout_pydantic_model import Workout, WorkoutCreate

workout_router = APIRouter()


# @workout_router.get("/workout/", tags=["workouts"], response_model=User)
# async def read_workout(
#     mobile_number: str,
#     db: Session = Depends(get_db)
# ):
#     workout = workout_crud.get_workout(db=db, mobile_number=mobile_number)
#     return workout


@workout_router.post("/workout/", tags=["workouts"], response_model=Workout)
async def create_workout(workout: WorkoutCreate, db: Session = Depends(get_db)):
    COMPETITOR_ROLE_ID = None
    if workout.competition:
        create_user_competition_relation(
            db, workout.user, workout.competition, COMPETITOR_ROLE_ID)
        event_id = get_competition(db, workout.competition).event
        if event_id:
            create_user_event_relation(
                db, workout.user, event_id, COMPETITOR_ROLE_ID
            )
    return workout_crud.create_workout(db=db, workout=workout)
