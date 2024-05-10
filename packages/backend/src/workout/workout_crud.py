from datetime import date

from sqlalchemy.orm import Session

from ..competition.competition_orm_model import Competition
from .workout_orm_model import Workout
from .workout_pydantic_model import WorkoutCreate


def get_workout_by_event(
    db: Session,
    user_id: int,
    event_id: int,
    competition_date: date
) -> Workout | None:

    workout = db.query(Workout).outerjoin(Competition). \
        filter(
            Workout.user == user_id,
            Competition.event == event_id,
            Competition.date == competition_date
    ).first()

    return workout


def get_user_workouts(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100
) -> list[Workout]:
    return db.query(Workout)\
             .filter(Workout.user == user_id)\
             .offset(skip)\
             .limit(limit)\
             .all()


def get_competition_workouts(
        db: Session,
        competition_id: int
) -> list[Workout]:
    return db.query(Workout)\
             .filter(Workout.competition == competition_id)\
             .all()


def create_workout(
    db: Session,
    workout: WorkoutCreate
) -> Workout:

    db_workout = Workout(**workout.model_dump())
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)
    return db_workout

# TODO: update_workout, delete
