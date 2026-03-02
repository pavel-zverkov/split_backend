from datetime import date as date_type, datetime

from pydantic import BaseModel

from ..enums.sport_kind import SportKind
from ..enums.start_format import StartFormat
from ..enums.competition_status import CompetitionStatus
from ..enums.event_role import EventRole
from ..enums.event_position import EventPosition


class CompetitionCreate(BaseModel):
    name: str
    description: str | None = None
    date: date_type
    sport_kind: SportKind | None = None
    start_format: StartFormat = StartFormat.SEPARATED_START
    location: str | None = None
    start_time: datetime | None = None


class CompetitionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    date: date_type | None = None
    start_format: StartFormat | None = None
    location: str | None = None
    status: CompetitionStatus | None = None
    start_time: datetime | None = None


class CompetitionResponse(BaseModel):
    id: int
    event_id: int
    name: str
    description: str | None = None
    date: date_type
    sport_kind: SportKind | None = None
    start_format: StartFormat
    location: str | None = None
    status: CompetitionStatus
    start_time: datetime | None = None
    registrations_count: int = 0
    distances_count: int = 0
    created_at: datetime

    model_config = {'from_attributes': True}


class CompetitionListItem(BaseModel):
    id: int
    name: str
    date: date_type
    sport_kind: SportKind | None = None
    start_format: StartFormat
    location: str | None = None
    status: CompetitionStatus
    start_time: datetime | None = None
    registrations_count: int = 0
    distances_count: int = 0

    model_config = {'from_attributes': True}


class CompetitionListResponse(BaseModel):
    competitions: list[CompetitionListItem]
    total: int
    limit: int
    offset: int


class EventBrief(BaseModel):
    id: int
    name: str

    model_config = {'from_attributes': True}


class MyRegistrationBrief(BaseModel):
    id: int
    competition_class: str | None = None
    bib_number: str | None = None
    start_time: datetime | None = None
    status: str

    model_config = {'from_attributes': True}


class CompetitionDetailResponse(BaseModel):
    id: int
    event_id: int
    event: EventBrief
    name: str
    description: str | None = None
    date: date_type
    sport_kind: SportKind | None = None
    start_format: StartFormat
    location: str | None = None
    status: CompetitionStatus
    start_time: datetime | None = None
    registrations_count: int = 0
    distances_count: int = 0
    team_count: int = 0
    my_registration: MyRegistrationBrief | None = None
    created_at: datetime

    model_config = {'from_attributes': True}


# Team schemas
class TeamUserBrief(BaseModel):
    id: int
    username_display: str
    first_name: str
    last_name: str | None = None

    model_config = {'from_attributes': True}


class CompetitionTeamItem(BaseModel):
    user: TeamUserBrief
    role: EventRole
    position: EventPosition | None = None
    inherited: bool = True

    model_config = {'from_attributes': True}


class CompetitionTeamListResponse(BaseModel):
    team: list[CompetitionTeamItem]
    total: int
    limit: int
    offset: int


class AssignTeamMemberRequest(BaseModel):
    user_id: int
    role: EventRole


class CompetitionTeamResponse(BaseModel):
    user_id: int
    competition_id: int
    role: EventRole
    position: EventPosition | None = None
    inherited: bool = False

    model_config = {'from_attributes': True}


# Legacy compatibility
class Competition(CompetitionCreate):
    id: int

    model_config = {'from_attributes': True}
