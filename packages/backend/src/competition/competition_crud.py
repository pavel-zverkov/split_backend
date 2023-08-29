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
    class_list: list[str],
    control_point_list: list[str],
    kind: SportKind = SportKind.RUN,
    format: str = '',
    event: int | None = None
) -> None:

    db_competition = Competition(
        name=name,
        date=date,
        class_list=class_list,
        control_point_list=control_point_list,
        kind=kind,
        format=format,
        event=event
    )
    db.add(db_competition)
    db.commit()
    db.refresh(db_competition)
    return db_competition

# TODO: update_competition, delete_competition
