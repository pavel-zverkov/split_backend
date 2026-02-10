from datetime import date, datetime

from pydantic import BaseModel

from ..enums.qualification_type import QualificationType
from ..enums.sport_kind import SportKind


class QualificationCreate(BaseModel):
    type: QualificationType
    sport_kind: SportKind
    rank: str
    issued_date: date | None = None
    valid_until: date | None = None
    document_number: str | None = None


class QualificationUpdate(BaseModel):
    rank: str | None = None
    issued_date: date | None = None
    valid_until: date | None = None
    document_number: str | None = None


class QualificationResponse(BaseModel):
    id: int
    type: QualificationType
    sport_kind: SportKind
    rank: str
    issued_date: date | None = None
    valid_until: date | None = None
    document_number: str | None = None
    confirmed: bool | None = None
    created_at: datetime

    model_config = {'from_attributes': True}


class QualificationPublicResponse(BaseModel):
    """Response for viewing other users' qualifications - document_number hidden."""
    id: int
    type: QualificationType
    sport_kind: SportKind
    rank: str
    issued_date: date | None = None
    valid_until: date | None = None
    confirmed: bool | None = None

    model_config = {'from_attributes': True}


class QualificationsListResponse(BaseModel):
    qualifications: list[QualificationResponse]


class QualificationsPublicListResponse(BaseModel):
    qualifications: list[QualificationPublicResponse]
