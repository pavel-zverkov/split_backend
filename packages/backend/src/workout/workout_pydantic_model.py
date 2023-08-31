from datetime import date, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel

from ..enums.enum_sport_kind import SportKind

if TYPE_CHECKING:
    from ..user.user_pydantic_model import User


class WorkoutCreate(BaseModel):
    user: int
    date: datetime
    sport_kind: SportKind = SportKind.RUN
    competition: int | None = None
    fit_file: str | None = None
    gpx_file: str | None = None
    tcx_file: str | None = None
    splits: dict | None = None


class Workout(WorkoutCreate):

    id: int

    class Config:
        orm_mode = True


class WorkoutCreateByUser(BaseModel):
    user_first_name: str
    user_last_name: str
    user_birthdate: date
    date: datetime
    sport_kind: SportKind = SportKind.RUN
    competition_name: str | None = None
    fit_file: str | None = None
    gpx_file: str | None = None
    tcx_file: str | None = None
    splits: dict | None = None
