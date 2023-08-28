from datetime import datetime

from ..enums.enum_sport_kind import SportKind
from sqlalchemy.orm import Session

from .event_orm_model import Event


def get_event(db: Session, event_id: int) -> None:
    return db.query(Event).filter(Event.id == event_id).first()


def create_event(
    db: Session,
    name: str,
    date: datetime,
    sport_kind: SportKind = SportKind.RUN,
) -> None:

    db_event = Event(
        date=date,
        sport_kind=sport_kind,
        name=name
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

# TODO: update_event, delete_event
