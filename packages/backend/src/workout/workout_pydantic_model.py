from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel

from ..enums.enum_sport_kind import SportKind

if TYPE_CHECKING:
    from ..user.user_pydantic_model import User


class Workout(BaseModel):

    id: int
    date: datetime
    sport_kind: SportKind = SportKind.RUN
    user: int
    event: int | None
    fit_file: str | None
    gpx_file: str | None
    tcx_file: str | None
    splits: dict | None
    owner: 'User'
