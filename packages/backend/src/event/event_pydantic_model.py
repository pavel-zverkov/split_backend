from datetime import datetime

from pydantic import BaseModel

from ..enums.enum_sport_kind import SportKind
from ..enums.enum_status import Status


class Event(BaseModel):

    id: int
    name: str
    date: datetime
    sport_kind: SportKind
