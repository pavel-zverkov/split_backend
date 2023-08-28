from datetime import datetime

from ..enums.enum_sport_kind import SportKind
from sqlalchemy.orm import Session

from .workout_orm_model import Workout


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
    date: datetime,
    user_id: int,
    event: int | None = None,
    fit_file: str | None = None,
    gpx_file: str | None = None,
    tcx_file: str | None = None,
    splits: dict | None = None,
    sport_kind: SportKind = SportKind.RUN,
) -> None:

    db_workout = Workout(
        date=date,
        sport_kind=sport_kind,
        user=user_id,
        event=event,
        fit_file=fit_file,
        gpx_file=gpx_file,
        tcx_file=tcx_file,
        splits=splits
    )
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)
    return db_workout

# TODO: update_workout, delete
