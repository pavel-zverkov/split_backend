from datetime import datetime

from pydantic import BaseModel, Field

from ..enums.registration_status import RegistrationStatus


class RegisterRequest(BaseModel):
    competition_class: str = Field(alias='class')

    model_config = {'populate_by_name': True}


class RegistrationResponse(BaseModel):
    id: int
    user_id: int
    competition_id: int
    competition_class: str | None = Field(None, alias='class')
    bib_number: str | None = None
    start_time: datetime | None = None
    status: RegistrationStatus
    created_at: datetime

    model_config = {'from_attributes': True, 'populate_by_name': True}


class RegistrationUserBrief(BaseModel):
    id: int
    username_display: str
    first_name: str
    last_name: str | None = None
    logo: str | None = None

    model_config = {'from_attributes': True}


class RegistrationItem(BaseModel):
    id: int
    user: RegistrationUserBrief
    competition_class: str | None = Field(None, alias='class')
    bib_number: str | None = None
    start_time: datetime | None = None
    status: RegistrationStatus

    model_config = {'from_attributes': True, 'populate_by_name': True}


class RegistrationsListResponse(BaseModel):
    registrations: list[RegistrationItem]
    total: int
    limit: int
    offset: int


class UpdateRegistrationRequest(BaseModel):
    bib_number: str | None = None
    start_time: datetime | None = None
    status: RegistrationStatus | None = None
    competition_class: str | None = Field(None, alias='class')

    model_config = {'populate_by_name': True}


class BatchRegistrationItem(BaseModel):
    registration_id: int
    bib_number: str | None = None
    start_time: datetime | None = None


class BatchUpdateRequest(BaseModel):
    registrations: list[BatchRegistrationItem]
    set_status: RegistrationStatus = RegistrationStatus.CONFIRMED


class BatchUpdateResultItem(BaseModel):
    registration_id: int
    bib_number: str | None = None
    status: RegistrationStatus


class BatchUpdateResponse(BaseModel):
    updated: int
    registrations: list[BatchUpdateResultItem]


# Start list schemas
class ClubBrief(BaseModel):
    id: int
    name: str

    model_config = {'from_attributes': True}


class StartListUserBrief(BaseModel):
    id: int
    username_display: str
    first_name: str
    last_name: str | None = None
    club: ClubBrief | None = None

    model_config = {'from_attributes': True}


class StartListItem(BaseModel):
    bib_number: str | None = None
    start_time: datetime | None = None
    competition_class: str | None = Field(None, alias='class')
    user: StartListUserBrief

    model_config = {'from_attributes': True, 'populate_by_name': True}


class ClassSummary(BaseModel):
    competition_class: str = Field(alias='class')
    count: int
    first_start: datetime | None = None

    model_config = {'populate_by_name': True}


class CompetitionBrief(BaseModel):
    id: int
    name: str
    date: str

    model_config = {'from_attributes': True}


class StartListResponse(BaseModel):
    competition: CompetitionBrief
    start_list: list[StartListItem]
    classes: list[ClassSummary]
    total: int
