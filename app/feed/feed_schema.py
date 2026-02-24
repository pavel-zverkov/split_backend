from datetime import date
from typing import Literal

from pydantic import BaseModel

from ..enums.competition_status import CompetitionStatus
from ..enums.event_status import EventStatus
from ..enums.sport_kind import SportKind


class FeedCompetitionItem(BaseModel):
    id: int
    name: str
    date: date
    status: CompetitionStatus
    registrations_count: int = 0
    distances_count: int = 0


class FeedEventBrief(BaseModel):
    id: int
    name: str
    logo: str | None
    sport_kind: SportKind
    status: EventStatus
    location: str | None
    participants_count: int


class FeedItem(BaseModel):
    type: Literal["single", "multi_stage_group"]
    event: FeedEventBrief
    date: date
    competition: FeedCompetitionItem | None = None
    competitions: list[FeedCompetitionItem] = []


class FeedResponse(BaseModel):
    items: list[FeedItem]
    total: int
    limit: int
    offset: int
