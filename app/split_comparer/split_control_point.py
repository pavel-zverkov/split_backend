from dataclasses import dataclass
from datetime import datetime


@dataclass
class ControlPoint:
    id: str
    split_time: datetime
    cumulative_time: datetime
    place: int
