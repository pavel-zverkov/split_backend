from datetime import date, datetime

from pydantic import BaseModel

from ..enums.sport_kind import SportKind
from ..enums.event_status import EventStatus
from ..enums.event_role import EventRole
from ..enums.event_position import EventPosition
from ..enums.privacy import Privacy
from ..enums.participation_status import ParticipationStatus


class EventCreate(BaseModel):
    name: str
    description: str | None = None
    start_date: date
    end_date: date
    location: str | None = None
    sport_kind: SportKind
    privacy: Privacy = Privacy.PUBLIC
    status: EventStatus = EventStatus.PLANNED
    max_participants: int | None = None


class EventUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    location: str | None = None
    sport_kind: SportKind | None = None
    privacy: Privacy | None = None
    status: EventStatus | None = None
    max_participants: int | None = None


class EventOrganizerBrief(BaseModel):
    id: int
    username_display: str
    first_name: str

    model_config = {'from_attributes': True}


class EventResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    start_date: date
    end_date: date
    location: str | None = None
    sport_kind: SportKind
    privacy: Privacy
    status: EventStatus
    max_participants: int | None = None
    organizer_id: int
    competitions_count: int
    team_count: int
    participants_count: int
    created_at: datetime

    model_config = {'from_attributes': True}


class EventDetailResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    start_date: date
    end_date: date
    location: str | None = None
    sport_kind: SportKind
    privacy: Privacy
    status: EventStatus
    max_participants: int | None = None
    organizer: EventOrganizerBrief
    competitions_count: int
    participants_count: int
    team_count: int
    my_role: EventRole | None = None
    my_position: EventPosition | None = None
    created_at: datetime

    model_config = {'from_attributes': True}


class EventListItem(BaseModel):
    id: int
    name: str
    start_date: date
    end_date: date
    location: str | None = None
    sport_kind: SportKind
    privacy: Privacy
    status: EventStatus
    competitions_count: int
    participants_count: int
    my_role: EventRole | None = None

    model_config = {'from_attributes': True}


class EventListResponse(BaseModel):
    events: list[EventListItem]
    total: int
    limit: int
    offset: int


class TeamMemberUserBrief(BaseModel):
    id: int
    username_display: str
    first_name: str
    last_name: str | None = None
    logo: str | None = None

    model_config = {'from_attributes': True}


class TeamMemberItem(BaseModel):
    id: int
    user: TeamMemberUserBrief
    role: EventRole
    position: EventPosition | None = None
    joined_at: datetime | None = None

    model_config = {'from_attributes': True}


class TeamListResponse(BaseModel):
    team: list[TeamMemberItem]
    total: int
    limit: int
    offset: int


class AddTeamMemberRequest(BaseModel):
    user_id: int
    role: EventRole
    position: EventPosition | None = None


class TeamMemberResponse(BaseModel):
    id: int
    user_id: int
    event_id: int
    role: EventRole
    position: EventPosition | None = None
    status: ParticipationStatus
    joined_at: datetime | None = None

    model_config = {'from_attributes': True}


class UpdateTeamMemberRequest(BaseModel):
    role: EventRole | None = None
    position: EventPosition | None = None


class TransferOwnershipRequest(BaseModel):
    new_organizer_id: int


class TransferOwnershipResponse(BaseModel):
    id: int
    name: str
    organizer_id: int
    message: str


# ===== Event Participation Schemas =====

class CompetitionBrief(BaseModel):
    id: int
    name: str

    model_config = {'from_attributes': True}


class JoinEventRequest(BaseModel):
    role: EventRole | None = None
    competition_ids: list[int] | str | None = None  # list of IDs or "all"
    token: str | None = None  # invite token


class ParticipantUserBrief(BaseModel):
    id: int
    username_display: str
    first_name: str
    last_name: str | None = None
    logo: str | None = None

    model_config = {'from_attributes': True}


class ParticipationResponse(BaseModel):
    id: int
    user_id: int
    event_id: int
    role: EventRole
    position: EventPosition | None = None
    status: ParticipationStatus
    competitions: list[CompetitionBrief] = []
    joined_at: datetime | None = None

    model_config = {'from_attributes': True}


class ParticipantItem(BaseModel):
    id: int
    user: ParticipantUserBrief
    status: ParticipationStatus
    competitions: list[CompetitionBrief] = []
    joined_at: datetime | None = None

    model_config = {'from_attributes': True}


class ParticipantsListResponse(BaseModel):
    participants: list[ParticipantItem]
    total: int
    limit: int
    offset: int


class RequestItem(BaseModel):
    id: int
    user: ParticipantUserBrief
    role: EventRole
    competitions: list[CompetitionBrief] = []
    created_at: datetime

    model_config = {'from_attributes': True}


class RequestsListResponse(BaseModel):
    requests: list[RequestItem]
    total: int
    limit: int
    offset: int


class UpdateRequestStatus(BaseModel):
    status: ParticipationStatus


class MyParticipationCompetition(BaseModel):
    id: int
    name: str
    registration_id: int | None = None
    competition_class: str | None = None
    bib_number: str | None = None
    start_time: datetime | None = None

    model_config = {'from_attributes': True}


class MyParticipationResponse(BaseModel):
    id: int
    event_id: int
    role: EventRole
    position: EventPosition | None = None
    status: ParticipationStatus
    competitions: list[MyParticipationCompetition] = []
    joined_at: datetime | None = None

    model_config = {'from_attributes': True}


class RecruitmentSettingsUpdate(BaseModel):
    recruitment_open: bool | None = None
    needed_roles: list[str] | None = None


class RecruitmentSettingsResponse(BaseModel):
    recruitment_open: bool
    needed_roles: list[str] | None = None


class CreateInviteRequest(BaseModel):
    role: EventRole
    position: EventPosition | None = None
    competition_ids: list[int] | None = None
    expires_at: datetime | None = None
    max_uses: int | None = 1


class InviteCreatorBrief(BaseModel):
    id: int
    username_display: str

    model_config = {'from_attributes': True}


class InviteResponse(BaseModel):
    id: int
    token: str
    role: EventRole
    position: EventPosition | None = None
    competition_ids: list[int] | None = None
    expires_at: datetime | None = None
    max_uses: int | None = None
    uses_count: int
    link: str | None = None
    created_at: datetime

    model_config = {'from_attributes': True}


class InviteListItem(BaseModel):
    id: int
    token: str
    role: EventRole
    position: EventPosition | None = None
    competition_ids: list[int] | None = None
    expires_at: datetime | None = None
    max_uses: int | None = None
    uses_count: int
    created_by: InviteCreatorBrief
    created_at: datetime

    model_config = {'from_attributes': True}


class InvitesListResponse(BaseModel):
    invites: list[InviteListItem]
    total: int


class AddParticipantRequest(BaseModel):
    user_id: int
    role: EventRole = EventRole.PARTICIPANT
    position: EventPosition | None = None
