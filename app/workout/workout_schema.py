from datetime import datetime

from pydantic import BaseModel

from ..enums.sport_kind import SportKind
from ..enums.workout_status import WorkoutStatus
from ..enums.privacy import Privacy


# ===== Request Schemas =====

class WorkoutCreate(BaseModel):
    title: str | None = None
    description: str | None = None
    sport_kind: SportKind
    start_datetime: datetime
    finish_datetime: datetime | None = None
    duration_seconds: int | None = None
    distance_meters: int | None = None
    elevation_gain: int | None = None
    privacy: Privacy = Privacy.PRIVATE

    model_config = {'from_attributes': True}


class WorkoutUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    sport_kind: SportKind | None = None
    privacy: Privacy | None = None

    model_config = {'from_attributes': True}


# ===== Brief Schemas =====

class WorkoutOwnerBrief(BaseModel):
    id: int
    username_display: str
    first_name: str
    last_name: str | None = None

    model_config = {'from_attributes': True}


class WorkoutUserBrief(BaseModel):
    id: int
    username_display: str
    first_name: str

    model_config = {'from_attributes': True}


class LinkedResultBrief(BaseModel):
    id: int
    competition_id: int
    competition_name: str
    position: int | None = None
    time_total: int | None = None

    model_config = {'from_attributes': True}


class WorkoutSplitResponse(BaseModel):
    id: int
    sequence: int
    control_point: str | None = None
    distance_meters: int | None = None
    cumulative_time: int
    split_time: int

    model_config = {'from_attributes': True}


class WorkoutArtifactBrief(BaseModel):
    id: int
    kind: str
    file_name: str

    model_config = {'from_attributes': True}


# ===== Response Schemas =====

class WorkoutResponse(BaseModel):
    id: int
    user_id: int
    title: str | None = None
    description: str | None = None
    sport_kind: SportKind
    privacy: Privacy
    status: WorkoutStatus
    start_datetime: datetime
    finish_datetime: datetime | None = None
    duration_seconds: int | None = None
    distance_meters: int | None = None
    elevation_gain: int | None = None
    has_splits: bool = False
    artifacts_count: int = 0
    created_at: datetime

    model_config = {'from_attributes': True}


class WorkoutListItem(BaseModel):
    id: int
    title: str | None = None
    sport_kind: SportKind
    privacy: Privacy
    status: WorkoutStatus
    start_datetime: datetime
    duration_seconds: int | None = None
    distance_meters: int | None = None
    elevation_gain: int | None = None
    has_splits: bool = False
    linked_result: LinkedResultBrief | None = None
    created_at: datetime

    model_config = {'from_attributes': True}


class WorkoutsListResponse(BaseModel):
    workouts: list[WorkoutListItem]
    total: int
    limit: int
    offset: int


class WorkoutDetailResponse(BaseModel):
    id: int
    user: WorkoutOwnerBrief
    title: str | None = None
    description: str | None = None
    sport_kind: SportKind
    privacy: Privacy
    status: WorkoutStatus
    start_datetime: datetime
    finish_datetime: datetime | None = None
    duration_seconds: int | None = None
    distance_meters: int | None = None
    elevation_gain: int | None = None
    splits: list[WorkoutSplitResponse] | None = None
    artifacts: list[WorkoutArtifactBrief] | None = None
    linked_result: LinkedResultBrief | None = None
    created_at: datetime

    model_config = {'from_attributes': True}


class UserWorkoutsResponse(BaseModel):
    user: WorkoutUserBrief
    workouts: list[WorkoutListItem]
    total: int
    limit: int
    offset: int
