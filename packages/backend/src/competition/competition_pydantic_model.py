from datetime import date

from pydantic import BaseModel

from ..enums.enum_sport_kind import SportKind


class CompetitionCreate(BaseModel):
    name: str
    date: date
    class_list: list[str]
    control_point_list: list[str]
    sport_kind: SportKind | None = SportKind.RUN
    format: str | None = None
    description: str | None = None
    location: str | None = None
    event: int | None = None


class Competition(CompetitionCreate):

    id: int

    class Config:
        orm_mode = True
