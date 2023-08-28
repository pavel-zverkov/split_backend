from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from ..user.user_pydantic_model import User


class Workout(BaseModel):

    id: int
    date: datetime
    user: int
    event: int
    fit_file: str
    gpx_file: str
    tcx_file: str
    splits: dict
    owner: 'User'
