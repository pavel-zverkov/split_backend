from datetime import date

from pydantic import BaseModel

from ..enums.enum_gender import Gender
from ..enums.enum_qualify import Qualify
from ..workout.workout_pydantic_model import Workout


class UserCreate(BaseModel):
    mobile_number: str | None = None
    first_name: str
    last_name: str | None = None
    birthdate: date | None = None
    gender: Gender | None = None
    qualify: Qualify | None = None
    is_active: bool = True


class User(UserCreate):

    id: int
    workouts: list[Workout] = []

    class Config:
        orm_mode = True
