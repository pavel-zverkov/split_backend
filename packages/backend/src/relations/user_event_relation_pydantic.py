from pydantic import BaseModel


class UserEventRelation(BaseModel):

    id: int
    user: int
    event: int
    role: int
