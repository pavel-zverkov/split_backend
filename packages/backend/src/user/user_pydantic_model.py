from datetime import datetime

from pydantic import BaseModel

from ..enums.enum_gender import Gender
from ..enums.enum_qualify import Qualify
from ..workout.workout_pydantic_model import Workout


class UserCreate(BaseModel):
    mobile_number: str
    first_name: str
    last_name: str | None = None
    birthdate: datetime | None = None
    gender: Gender | None = None
    qualify: Qualify | None = None


class User(UserCreate):

    id: int
    is_active: bool = True
    workouts: list[Workout] = []

    class Config:
        orm_mode = True
