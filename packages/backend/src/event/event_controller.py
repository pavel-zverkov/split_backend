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
    db: Session = Depends(get_db)
):
    event = event_crud.get_event(db, event_name)
    return event


@event_router.post(
    "/event/",
    tags=["events"],
    response_model=Event
)
async def create_event(event: EventCreate, db: Session = Depends(get_db)):
    return event_crud.create_event(db=db, event=event)
