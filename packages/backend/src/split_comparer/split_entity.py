from dataclasses import dataclass
from datetime import datetime, time

from ..competition.competition_orm_model import Competition
from .split_control_point import ControlPoint


@dataclass
class Split:
    competition: Competition
    person: str
    class_code: str
    ctrl_points_info: dict[str, ControlPoint]
    result: time | None
