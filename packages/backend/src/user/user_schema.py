from datetime import date

from pydantic import BaseModel

from ..enums.gender import Gender
from ..workout.workout_schema import Workout


class UserCreate(BaseModel):
    username: str
    first_name: str
    last_name: str | None = None
    birthday: date | None = None
    is_active: bool = True


class User(UserCreate):

    id: int
    gender: Gender | None = None
    workouts: list[Workout] = []

    class Config:
        orm_mode = True
