from datetime import datetime

from pydantic import BaseModel, Field

from ..enums.result_status import ResultStatus


# ===== Split Schemas =====

class SplitInput(BaseModel):
    control_point: str
    cumulative_time: int


class SplitResponse(BaseModel):
    control_point: str
    sequence: int
    cumulative_time: int
    split_time: int

    model_config = {'from_attributes': True}


class SplitDetailResponse(BaseModel):
    control_point: str
    sequence: int
    cumulative_time: int
    split_time: int
    position: int | None = None
    time_behind_best: int | None = None

    model_config = {'from_attributes': True}


# ===== User/Club Brief =====

class ClubBrief(BaseModel):
    id: int
    name: str

    model_config = {'from_attributes': True}


class ResultUserBrief(BaseModel):
    id: int
    username_display: str
    first_name: str
    last_name: str | None = None
    club: ClubBrief | None = None

    model_config = {'from_attributes': True}


class CompetitionBrief(BaseModel):
    id: int
    name: str
    date: str

    model_config = {'from_attributes': True}


# ===== Request Schemas =====

class ResultCreate(BaseModel):
    user_id: int
    competition_class: str | None = Field(None, alias='class')
    time_total: int | None = None
    status: ResultStatus = ResultStatus.OK
    splits: list[SplitInput] | None = None

    model_config = {'populate_by_name': True}


class ResultUpdate(BaseModel):
    time_total: int | None = None
    status: ResultStatus | None = None
    competition_class: str | None = Field(None, alias='class')
    splits: list[SplitInput] | None = None

    model_config = {'populate_by_name': True}


class LinkWorkoutRequest(BaseModel):
    workout_id: int


# ===== Response Schemas =====

class ResultResponse(BaseModel):
    id: int
    user_id: int
    competition_id: int
    distance_id: int | None = None
    workout_id: int | None = None
    competition_class: str | None = Field(None, alias='class')
    position: int | None = None
    position_overall: int | None = None
    time_total: int | None = None
    time_behind_leader: int | None = None
    status: ResultStatus
    splits: list[SplitResponse] | None = None
    created_at: datetime

    model_config = {'from_attributes': True, 'populate_by_name': True}


class ResultListItem(BaseModel):
    id: int
    user: ResultUserBrief
    competition_class: str | None = Field(None, alias='class')
    position: int | None = None
    time_total: int | None = None
    time_behind_leader: int | None = None
    status: ResultStatus
    has_splits: bool = False

    model_config = {'from_attributes': True, 'populate_by_name': True}


class ClassSummary(BaseModel):
    competition_class: str = Field(alias='class')
    count: int
    leader_time: int | None = None

    model_config = {'populate_by_name': True}


class ResultsListResponse(BaseModel):
    competition: CompetitionBrief
    results: list[ResultListItem]
    classes: list[ClassSummary]
    total: int
    limit: int
    offset: int


class ResultDetailResponse(BaseModel):
    id: int
    user: ResultUserBrief
    competition: CompetitionBrief
    workout_id: int | None = None
    competition_class: str | None = Field(None, alias='class')
    position: int | None = None
    position_overall: int | None = None
    time_total: int | None = None
    time_behind_leader: int | None = None
    status: ResultStatus
    splits: list[SplitDetailResponse] | None = None
    created_at: datetime

    model_config = {'from_attributes': True, 'populate_by_name': True}


class RecalculateResponse(BaseModel):
    recalculated: bool
    results_count: int
    classes_count: int


class ImportResultItem(BaseModel):
    row: int
    bib_number: str
    error: str


class ImportResponse(BaseModel):
    imported: int
    updated: int
    skipped: int
    errors: list[ImportResultItem]


class LinkWorkoutResponse(BaseModel):
    id: int
    workout_id: int
    message: str
