from datetime import datetime

from pydantic import BaseModel

from ..enums.total_result_status import TotalResultStatus


# ===== Rules Sub-models =====

class TotalRulesSource(BaseModel):
    competition_ids: list[int] | None = None
    classes: list[str] | None = None


class TotalRulesScore(BaseModel):
    type: str = 'time'  # time, position, formula
    expression: str | None = None


class TotalRulesAggregation(BaseModel):
    method: str = 'sum'  # sum, min, max, avg
    best_count: int | None = None
    min_stages: int | None = None


class TotalRulesPenalties(BaseModel):
    dsq_handling: str = 'exclude'  # exclude, max_time, penalty
    dns_handling: str = 'exclude'  # exclude, max_time, penalty
    penalty_value: float | None = None


class TotalRules(BaseModel):
    source: TotalRulesSource = TotalRulesSource()
    score: TotalRulesScore = TotalRulesScore()
    aggregation: TotalRulesAggregation = TotalRulesAggregation()
    penalties: TotalRulesPenalties = TotalRulesPenalties()
    sort_order: str = 'asc'  # asc (less is better) or desc


# ===== Request Schemas =====

class TotalConfigCreate(BaseModel):
    name: str
    rules: TotalRules | None = None
    auto_calculate: bool = True
    preset: str | None = None  # sum_time, sum_positions, best_n_time, iof_points


class TotalConfigUpdate(BaseModel):
    name: str | None = None
    rules: TotalRules | None = None
    auto_calculate: bool | None = None


# ===== Response Schemas =====

class TotalConfigResponse(BaseModel):
    id: int
    event_id: int
    name: str
    rules: dict
    auto_calculate: bool
    results_count: int = 0
    created_at: datetime

    model_config = {'from_attributes': True}


class TotalConfigListResponse(BaseModel):
    configs: list[TotalConfigResponse]
    total: int


# ===== Result Schemas =====

class TotalResultUserBrief(BaseModel):
    id: int
    username_display: str
    first_name: str
    last_name: str | None = None

    model_config = {'from_attributes': True}


class TotalResultItem(BaseModel):
    id: int
    user: TotalResultUserBrief
    class_: str | None = None
    total_value: float | None = None
    position: int | None = None
    position_overall: int | None = None
    stages_counted: int
    stages_total: int
    status: TotalResultStatus

    model_config = {'from_attributes': True}


class TotalResultsListResponse(BaseModel):
    results: list[TotalResultItem]
    total: int
    limit: int
    offset: int


class StageBreakdownItem(BaseModel):
    competition_id: int
    competition_name: str
    result_id: int | None = None
    time_total: int | None = None
    position: int | None = None
    score: float | None = None
    status: str | None = None


class TotalResultDetailResponse(BaseModel):
    id: int
    user: TotalResultUserBrief
    class_: str | None = None
    total_value: float | None = None
    position: int | None = None
    position_overall: int | None = None
    stages_counted: int
    stages_total: int
    status: TotalResultStatus
    stages: list[StageBreakdownItem] = []
    calculated_at: datetime

    model_config = {'from_attributes': True}
