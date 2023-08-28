from datetime import datetime

from ..enums.enum_sport_kind import SportKind
from sqlalchemy.orm import Session

from .competition_orm_model import Competition


def get_competition(db: Session, competition_id: int) -> None:
    return db.query(Competition).filter(Competition.id == competition_id).first()


def create_competition(
    db: Session,
    name: str,
    date: datetime,
    sport_kind: SportKind = SportKind.RUN,
) -> None:

    db_competition = Competition(
        date=date,
        sport_kind=sport_kind,
        name=name
    )
    db.add(db_competition)
    db.commit()
    db.refresh(db_competition)
    return db_competition

# TODO: update_competition, delete_competition
