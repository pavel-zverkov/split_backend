from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..competition.competition_crud import get_competition, get_competition_by_name
from ..database import get_db
from ..logger import logger
from ..user.user_crud import get_user_by_name
from ..user.user_schema import UserCreate
from . import workout_crud
from .workout_schema import (Workout,
                                     WorkoutCreate,
                                     WorkoutCreateByUser)


workout_router = APIRouter()


@workout_router.post("/workout/", tags=["workouts"], response_model=Workout)
async def create_workout(
    workout: WorkoutCreate,
    db: Session = Depends(get_db)
):
    # TODO: Create CompetitionRegistration and EventParticipation if competition is set
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
    logger.debug(workout.__dict__)

    user = get_user_by_name(
        db,
        workout.user_first_name,
        workout.user_last_name,
        workout.user_birthdate
    )

    if not user:
        # TODO: Use proper user creation flow with ghost users
        from ..user.user_model import User
        from ..enums.account_type import AccountType
        user = User(
            username=f"{workout.user_first_name}_{workout.user_last_name}".lower(),
            username_display=f"{workout.user_first_name}_{workout.user_last_name}".lower(),
            first_name=workout.user_first_name,
            last_name=workout.user_last_name,
            birthday=workout.user_birthdate,
            account_type=AccountType.GHOST,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    if workout.competition_name:
        competition = get_competition_by_name(
            db,
            workout.competition_name,
            workout.date.date(),
            workout.sport_kind
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
