from pydantic import BaseModel

from ..enums.enum_status import Status


class Event(BaseModel):

    id: int
    name: str
    status: Status
