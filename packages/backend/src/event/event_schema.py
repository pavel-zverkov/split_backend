from datetime import date

from pydantic import BaseModel

from ..enums.sport_kind import SportKind
from ..enums.event_status import EventStatus


class EventCreate(BaseModel):

    name: str
    start_date: date
    end_date: date
    sport_kind: SportKind = SportKind.RUN


class Event(EventCreate):

    id: int
    status: EventStatus

    class Config:
        orm_mode = True
