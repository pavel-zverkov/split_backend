from pydantic import BaseModel

from ..enums.enum_sport_kind import SportKind
from ..enums.enum_status import Status


class Competition(BaseModel):

    id: int
    name: str
    kind: SportKind
    status: Status = Status.PLANNED
