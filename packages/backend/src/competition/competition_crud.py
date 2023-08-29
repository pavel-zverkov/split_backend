from sqlalchemy.orm import Session

from .competition_orm_model import Competition
from .competition_pydantic_model import CompetitionCreate


def get_competition(db: Session, id: int):
    return db.query(Competition).filter(Competition.id == id).first()


def create_competition(
    db: Session,
    competition: CompetitionCreate
):

    db_competition = Competition(**competition.model_dump())
    db.add(db_competition)
    db.commit()
    db.refresh(db_competition)
    return db_competition

# TODO: update_competition, delete_competition
