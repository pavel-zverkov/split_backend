from datetime import datetime

from pydantic import BaseModel

from ..enums.control_point_type import ControlPointType


class ControlPointInput(BaseModel):
    code: str
    type: ControlPointType = ControlPointType.CONTROL


class DistanceCreate(BaseModel):
    name: str
    distance_meters: int | None = None
    climb_meters: int | None = None
    control_time: int | None = None  # seconds
    classes: list[str] | None = None
    control_points: list[ControlPointInput] | None = None


class DistanceUpdate(BaseModel):
    name: str | None = None
    distance_meters: int | None = None
    climb_meters: int | None = None
    control_time: int | None = None  # seconds
    classes: list[str] | None = None


class ControlPointResponse(BaseModel):
    id: int
    code: str
    sequence: int
    type: ControlPointType

    model_config = {'from_attributes': True}


class DistanceResponse(BaseModel):
    id: int
    competition_id: int
    name: str
    distance_meters: int | None = None
    climb_meters: int | None = None
    control_time: int | None = None
    classes: list[str] | None = None
    control_points: list[ControlPointResponse] = []
    created_at: datetime

    model_config = {'from_attributes': True}


class DistanceListItem(BaseModel):
    id: int
    name: str
    distance_meters: int | None = None
    climb_meters: int | None = None
    control_time: int | None = None
    classes: list[str] | None = None
    control_points_count: int = 0

    model_config = {'from_attributes': True}


class DistanceListResponse(BaseModel):
    distances: list[DistanceListItem]
    total: int
