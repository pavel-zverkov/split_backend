from dataclasses import dataclass
from datetime import datetime

from ..competition.competition_orm_model import Competition
from .split_control_point import ControlPoint


@dataclass
class Split:
    competition: Competition
    person: str
    class_code: str
    ctrl_points_info: list[ControlPoint]
    result: datetime.time | None
