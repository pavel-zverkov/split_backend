from datetime import date
from sqlalchemy.orm import Session

from .competition_orm_model import Competition
from .competition_pydantic_model import CompetitionCreate


def get_competition(db: Session, id: int) -> Competition | None:
    return db.query(Competition).filter(Competition.id == id).first()


def get_competition_by_name(
    db: Session,
    name: str,
    date: date,
    sport_kind: str
) -> Competition | None:
    return db.query(Competition)\
             .filter(
                 Competition.name == name,
                 Competition.sport_kind == sport_kind,
                 Competition.date == date)\
             .first()


def create_competition(
    db: Session,
    competition: CompetitionCreate
) -> Competition:

    db_competition = Competition(**competition.model_dump())
    db.add(db_competition)
    db.commit()
    db.refresh(db_competition)
    return db_competition

# TODO: update_competition, delete_competition
