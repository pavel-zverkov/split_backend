from datetime import date, datetime

from sqlalchemy.orm import Session

from ..enums.enum_status import Status
from .event_orm_model import Event
from .event_pydantic_model import EventCreate


def get_event(db: Session, event_id: int) -> Event | None:
    return db.query(Event).filter(Event.id == event_id).first()


def get_event_by_name(db: Session, event_name: str, sport_kind: str) -> Event | None:
    return db.query(Event)\
             .filter(
                 Event.name == event_name,
                 Event.sport_kind == sport_kind)\
             .first()


def create_event(
    db: Session,
    event: EventCreate
) -> Event:

    status = __get_status(event.start_date, event.end_date)
    db_event = Event(
        start_date=event.start_date,
        end_date=event.end_date,
        sport_kind=event.sport_kind,
        name=event.name,
        status=status
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


def __get_status(start_date: date, end_date: date) -> Status:
    NOW = datetime.now()
    if NOW.date() > end_date:
        return Status.CLOSED
    elif NOW.date() >= start_date and NOW.date() <= end_date:
        return Status.IN_PROGRESS
    return Status.PLANNED

# TODO: update_event, delete_event
