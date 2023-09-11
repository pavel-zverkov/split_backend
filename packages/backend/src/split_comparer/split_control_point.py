from dataclasses import dataclass
from datetime import time


@dataclass
class ControlPoint:
    id: str
    split_time: time
    cumulative_time: time
    place: int
