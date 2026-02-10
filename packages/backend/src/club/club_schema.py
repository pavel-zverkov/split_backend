from datetime import datetime

from pydantic import BaseModel

from ..enums.privacy import Privacy
from ..enums.club_role import ClubRole
from ..enums.membership_status import MembershipStatus


class ClubCreate(BaseModel):
    name: str
    description: str | None = None
    privacy: Privacy = Privacy.PUBLIC
    location: str | None = None


class ClubUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    privacy: Privacy | None = None
    location: str | None = None


class ClubOwnerBrief(BaseModel):
    id: int
    username_display: str
    first_name: str

    model_config = {'from_attributes': True}


class ClubResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    logo: str | None = None
    location: str | None = None
    privacy: Privacy
    owner_id: int
    members_count: int
    created_at: datetime

    model_config = {'from_attributes': True}


class ClubDetailResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    logo: str | None = None
    location: str | None = None
    privacy: Privacy
    owner: ClubOwnerBrief
    members_count: int
    membership_status: MembershipStatus | None = None
    membership_role: ClubRole | None = None
    created_at: datetime

    model_config = {'from_attributes': True}


class ClubListItem(BaseModel):
    id: int
    name: str
    logo: str | None = None
    location: str | None = None
    privacy: Privacy
    members_count: int
    membership_status: MembershipStatus | None = None

    model_config = {'from_attributes': True}


class ClubListResponse(BaseModel):
    clubs: list[ClubListItem]
    total: int
    limit: int
    offset: int


class ClubLogoResponse(BaseModel):
    logo: str


class MemberUserBrief(BaseModel):
    id: int
    username_display: str
    first_name: str
    last_name: str | None = None
    logo: str | None = None

    model_config = {'from_attributes': True}


class ClubMemberItem(BaseModel):
    id: int
    user: MemberUserBrief
    role: ClubRole
    status: MembershipStatus
    joined_at: datetime | None = None

    model_config = {'from_attributes': True}


class ClubMembersResponse(BaseModel):
    members: list[ClubMemberItem]
    total: int
    limit: int
    offset: int


class MembershipResponse(BaseModel):
    id: int
    user_id: int
    club_id: int
    role: ClubRole
    status: MembershipStatus
    joined_at: datetime | None = None
    created_at: datetime

    model_config = {'from_attributes': True}


class MembershipStatusUpdate(BaseModel):
    status: MembershipStatus


class MembershipRoleUpdate(BaseModel):
    role: ClubRole


class TransferOwnershipRequest(BaseModel):
    new_owner_id: int


class TransferOwnershipResponse(BaseModel):
    id: int
    name: str
    owner_id: int
    message: str
