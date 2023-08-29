from datetime import datetime

from sqlalchemy.orm import Session

from .workout_orm_model import Workout
from .workout_pydantic_model import WorkoutCreate


def get_workout(db: Session, workout_id: int) -> None:
    return db.query(Workout).filter(Workout.id == workout_id).first()


def get_user_workouts(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100
) -> None:
    return db.query(Workout)\
             .filter(Workout.user == user_id)\
             .offset(skip)\
             .limit(limit)\
             .all()


def create_workout(
    db: Session,
    workout: WorkoutCreate
) -> None:

    db_workout = Workout(**workout.model_dump())
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)
    return db_workout

# TODO: update_workout, delete
