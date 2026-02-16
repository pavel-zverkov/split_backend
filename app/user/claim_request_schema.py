from datetime import datetime

from pydantic import BaseModel

from ..enums.claim_status import ClaimStatus
from ..enums.claim_type import ClaimType


class ClaimRequest(BaseModel):
    ghost_user_ids: list[int]
    claim_type: ClaimType = ClaimType.EVENT


class UserBriefForClaim(BaseModel):
    id: int
    username_display: str

    model_config = {'from_attributes': True}


class ClaimRequestItem(BaseModel):
    id: int
    ghost_user_id: int
    status: ClaimStatus
    claim_type: ClaimType
    approver_id: int | None = None

    model_config = {'from_attributes': True}


class ClaimRequestResponse(BaseModel):
    claim_requests: list[ClaimRequestItem]


class ClaimRequestDetailItem(BaseModel):
    id: int
    ghost_user: UserBriefForClaim
    status: ClaimStatus
    claim_type: ClaimType
    created_at: datetime

    model_config = {'from_attributes': True}


class MyClaimRequestsResponse(BaseModel):
    claims: list[ClaimRequestDetailItem]


class ClaimerBrief(BaseModel):
    id: int
    username_display: str
    first_name: str

    model_config = {'from_attributes': True}


class PendingClaimItem(BaseModel):
    id: int
    claimer: ClaimerBrief
    ghost_user: UserBriefForClaim
    claim_type: ClaimType
    created_at: datetime

    model_config = {'from_attributes': True}


class PendingClaimsResponse(BaseModel):
    claims: list[PendingClaimItem]


class ClaimStatusUpdate(BaseModel):
    status: ClaimStatus
