from pydantic import BaseModel


# ===== Position Schema =====

class PositionSchema(BaseModel):
    lat: float
    lng: float

    model_config = {'from_attributes': True}


# ===== Request Schemas =====

class SplitCreate(BaseModel):
    sequence: int
    control_point: str | None = None
    distance_meters: int | None = None
    cumulative_time: int
    split_time: int
    position: PositionSchema | None = None

    model_config = {'from_attributes': True}


class SplitsCreateRequest(BaseModel):
    splits: list[SplitCreate]


class SplitUpdate(BaseModel):
    control_point: str | None = None
    distance_meters: int | None = None
    cumulative_time: int | None = None
    split_time: int | None = None
    position: PositionSchema | None = None

    model_config = {'from_attributes': True}


# ===== Response Schemas =====

class SplitResponse(BaseModel):
    id: int
    sequence: int
    control_point: str | None = None
    distance_meters: int | None = None
    cumulative_time: int
    split_time: int
    position: PositionSchema | None = None

    model_config = {'from_attributes': True}


class SplitsListResponse(BaseModel):
    workout_id: int
    splits: list[SplitResponse]
    total: int
