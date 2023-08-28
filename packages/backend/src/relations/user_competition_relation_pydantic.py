from pydantic import BaseModel


class UserCompetitionRelation(BaseModel):

    id: int
    user: int
    competition: int
    role: int
