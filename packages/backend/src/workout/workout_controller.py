from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..competition.competition_crud import (get_competition,
                                            get_competition_by_name)
from ..database import get_db
from ..logger import logger
from ..relations.user_competition_relation_crud import create_user_competition_relation
from ..relations.user_event_relation_crud import create_user_event_relation
from ..user.user_crud import create_user, get_user_by_name
from ..user.user_pydantic_model import UserCreate
from . import workout_crud
from .workout_pydantic_model import (Workout,
                                     WorkoutCreate,
                                     WorkoutCreateByUser)

COMPETITOR_ROLE_ID = None


workout_router = APIRouter()


# @workout_router.get("/workout/", tags=["workouts"], response_model=User)
# async def read_workout(
#     mobile_number: str,
#     db: Session = Depends(get_db)
# ):
#     workout = workout_crud.get_workout(db=db, mobile_number=mobile_number)
#     return workout


@workout_router.post("/workout/", tags=["workouts"], response_model=Workout)
async def create_workout(
    workout: WorkoutCreate,
    db: Session = Depends(get_db)
):

    if workout.competition:
        create_user_competition_relation(
            db,
            workout.user,
            workout.competition,
            COMPETITOR_ROLE_ID
        )

        event_id = get_competition(db, workout.competition).event
        if event_id:
            create_user_event_relation(
                db,
                workout.user,
                event_id,
                COMPETITOR_ROLE_ID
            )

    return workout_crud.create_workout(db=db, workout=workout)


@workout_router.post(
    "/workout/by_user",
    tags=["workouts"],
    response_model=Workout
)
async def create_workout_by_user(
    workout: WorkoutCreateByUser,
    db: Session = Depends(get_db)
):

    user = get_user_by_name(
        db,
        workout.user_first_name,
        workout.user_last_name,
        workout.user_birthdate
    )

    if not user:
        user_create = UserCreate(
            first_name=workout.user_first_name,
            last_name=workout.user_last_name,
            birthdate=workout.user_birthdate
        )
        user = create_user(db, user_create)

    if workout.competition_name:
        competition = get_competition_by_name(
            db,
            workout.competition_name,
            workout.date.date(),
            workout.sport_kind
        )

        if competition:
            create_user_competition_relation(
                db,
                user.id,
                competition.id,
                COMPETITOR_ROLE_ID
            )

            if competition.event:
                create_user_event_relation(
                    db,
                    user.id,
                    competition.event,
                    COMPETITOR_ROLE_ID
                )
    else:
        competition = None

    workout_create = WorkoutCreate(
        user=user.id,
        date=workout.date,
        sport_kind=workout.sport_kind,
        competition=competition.id if competition else None,
        fit_file=workout.fit_file,
        gpx_file=workout.gpx_file,
        tcx_file=workout.tcx_file,
        splits=workout.splits
    )

    return workout_crud.create_workout(db=db, workout=workout_create)
