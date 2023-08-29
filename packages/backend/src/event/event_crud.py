from datetime import datetime

from sqlalchemy.orm import Session

from ..enums.enum_sport_kind import SportKind
from ..enums.enum_status import Status
from .event_orm_model import Event


def get_event(db: Session, event_id: int) -> None:
    return db.query(Event).filter(Event.id == event_id).first()


def create_event(
    db: Session,
    name: str,
    start_date: datetime,
    end_date: datetime,
    sport_kind: SportKind = SportKind.RUN,
) -> None:

    status = __get_status(start_date, end_date)
    db_event = Event(
        start_date=start_date,
        end_date=end_date,
        sport_kind=sport_kind,
        name=name,
        status=status
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


def __get_status(start_date: datetime, end_date: datetime) -> Status:
    NOW = datetime.now()
    if NOW.date > end_date:
        return Status.CLOSED
    elif NOW.date >= start_date and NOW.date <= end_date:
        return Status.IN_PROGRESS
    return Status.PLANNED

# TODO: update_event, delete_event
