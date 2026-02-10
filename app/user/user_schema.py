from datetime import date, datetime

from pydantic import BaseModel, EmailStr, field_validator
import re

from ..enums.gender import Gender
from ..enums.privacy import Privacy
from ..enums.account_type import AccountType
from ..enums.follow_status import FollowStatus


class UserBase(BaseModel):
    first_name: str
    last_name: str | None = None
    birthday: date | None = None
    gender: Gender | None = None

    @field_validator('birthday')
    @classmethod
    def validate_birthday(cls, v: date | None) -> date | None:
        if v is not None and v > date.today():
            raise ValueError('Birthday cannot be in the future')
        return v


class UserCreate(UserBase):
    username: str

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username must contain only alphanumeric characters and underscores')
        return v.lower()


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    birthday: date | None = None
    gender: Gender | None = None
    bio: str | None = None
    privacy_default: Privacy | None = None
    email: EmailStr | None = None

    @field_validator('birthday')
    @classmethod
    def validate_birthday(cls, v: date | None) -> date | None:
        if v is not None and v > date.today():
            raise ValueError('Birthday cannot be in the future')
        return v


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class UserResponse(BaseModel):
    id: int
    username: str
    username_display: str
    email: str | None = None
    first_name: str
    last_name: str | None = None
    birthday: date | None = None
    gender: Gender | None = None
    logo: str | None = None
    bio: str | None = None
    privacy_default: Privacy | None = None
    account_type: AccountType
    created_at: datetime
    warnings: list[str] | None = None

    model_config = {'from_attributes': True}


class UserPublicProfile(BaseModel):
    id: int
    username_display: str
    first_name: str
    last_name: str | None = None
    logo: str | None = None
    bio: str | None = None
    account_type: AccountType
    follow_status: FollowStatus | None = None
    followers_count: int = 0
    following_count: int = 0
    workouts_count: int = 0

    model_config = {'from_attributes': True}


class UserBrief(BaseModel):
    id: int
    username_display: str
    first_name: str
    last_name: str | None = None
    account_type: AccountType

    model_config = {'from_attributes': True}


class UserSearchItem(BaseModel):
    id: int
    username_display: str
    first_name: str
    last_name: str | None = None
    account_type: AccountType

    model_config = {'from_attributes': True}


class UserSearchResponse(BaseModel):
    users: list[UserSearchItem]
    total: int
    limit: int
    offset: int


class GhostUserCreate(BaseModel):
    first_name: str
    last_name: str | None = None
    birthday: date | None = None
    gender: Gender | None = None

    @field_validator('birthday')
    @classmethod
    def validate_birthday(cls, v: date | None) -> date | None:
        if v is not None and v > date.today():
            raise ValueError('Birthday cannot be in the future')
        return v


class GhostUserResponse(BaseModel):
    id: int
    username: str
    username_display: str
    first_name: str
    last_name: str | None = None
    account_type: AccountType
    created_by: int

    model_config = {'from_attributes': True}


class CreatorBrief(BaseModel):
    id: int
    username_display: str

    model_config = {'from_attributes': True}


class GhostMatchItem(BaseModel):
    user_id: int
    username_display: str
    first_name: str
    last_name: str | None = None
    birthday: date | None = None
    created_by: CreatorBrief | None = None
    competitions_count: int = 0
    results_summary: str | None = None

    model_config = {'from_attributes': True}


class GhostMatchResponse(BaseModel):
    matches: list[GhostMatchItem]


class AvatarResponse(BaseModel):
    logo: str
