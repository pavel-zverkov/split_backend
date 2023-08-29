from datetime import datetime
from pydantic import BaseModel

from ..enums.enum_sport_kind import SportKind


class Competition(BaseModel):

    id: int
    name: str
    date: datetime
    class_list: list[str]
    control_point_list: list[str]
    kind: SportKind
    format: str
    event: int | None
