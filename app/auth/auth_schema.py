from pydantic import BaseModel, EmailStr, field_validator
import re

from ..enums.account_type import AccountType


class RegisterRequest(BaseModel):
    username: str
    password: str
    first_name: str
    last_name: str | None = None
    email: EmailStr | None = None

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username must contain only alphanumeric characters and underscores')
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        if len(v) > 50:
            raise ValueError('Username must be at most 50 characters')
        return v.lower()

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class LoginRequest(BaseModel):
    login: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class UserBrief(BaseModel):
    id: int
    username: str
    first_name: str
    account_type: AccountType

    model_config = {'from_attributes': True}


class TokenPayload(BaseModel):
    user_id: int
    username: str
    account_type: AccountType

    model_config = {'from_attributes': True}

    @classmethod
    def from_user(cls, user) -> 'TokenPayload':
        return cls(
            user_id=user.id,
            username=user.username,
            account_type=user.account_type,
        )


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'


class AuthResponse(BaseModel):
    user: UserBrief
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'


class RegisterResponse(AuthResponse):
    suggested_ghosts: list = []
