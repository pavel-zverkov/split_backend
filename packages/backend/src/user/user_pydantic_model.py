from datetime import datetime

from pydantic import BaseModel

from ..enums.enum_gender import Gender
from ..enums.enum_qualify import Qualify
from ..workout.workout_pydantic_model import Workout


class User(BaseModel):

    id: int
    mobile_number: str
    first_name: str
    last_name: str | None
    birthdate: datetime | None
    gender: Gender | None
    qualify: Qualify | None
    is_active: bool

    workouts: list[Workout] = []
