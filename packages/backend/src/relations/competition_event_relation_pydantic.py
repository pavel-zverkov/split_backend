
from pydantic import BaseModel


class CompetitionEventRelation(BaseModel):

    id: int
    competition: int
    event: int
