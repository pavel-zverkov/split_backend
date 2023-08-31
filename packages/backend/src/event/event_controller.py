from fastapi import (APIRouter,
                     Depends,
                     HTTPException)
from sqlalchemy.orm import Session

from ..database import get_db
from . import event_crud
from .event_pydantic_model import Event, EventCreate

event_router = APIRouter()


@event_router.get(
    "/event/",
    tags=["events"],
    response_model=Event
)
async def read_event(
    event_name: str,
    sport_kind: str,
    db: Session = Depends(get_db)
):
    event = event_crud.get_event_by_name(db, event_name, sport_kind)
    return event


@event_router.post(
    "/event/",
    tags=["events"],
    response_model=Event
)
async def create_event(event: EventCreate, db: Session = Depends(get_db)):
    db_event = event_crud.get_event_by_name(
        db, event.name, event.sport_kind)
    if db_event:
        raise HTTPException(
            status_code=400,
            detail=f"Event {event.name} for sport kind {event.sport_kind} already registered"
        )
    return event_crud.create_event(db=db, event=event)
