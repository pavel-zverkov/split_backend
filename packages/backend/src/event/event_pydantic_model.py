from datetime import datetime

from pydantic import BaseModel

from ..enums.enum_sport_kind import SportKind
from ..enums.enum_status import Status


class EventCreate(BaseModel):

    name: str
    start_date: datetime
    end_date: datetime
    sport_kind: SportKind = SportKind.RUN


class Event(EventCreate):

    id: int
    status: Status

    class Config:
        orm_mode = True
