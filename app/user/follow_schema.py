from datetime import datetime

from pydantic import BaseModel

from ..enums.follow_status import FollowStatus


class FollowResponse(BaseModel):
    id: int
    follower_id: int
    following_id: int
    status: FollowStatus
    created_at: datetime

    model_config = {'from_attributes': True}


class FollowStatusUpdate(BaseModel):
    status: FollowStatus


class FollowerItem(BaseModel):
    id: int
    username_display: str
    first_name: str
    last_name: str | None = None
    logo: str | None = None
    is_following: bool | None = None

    model_config = {'from_attributes': True}


class FollowersResponse(BaseModel):
    followers: list[FollowerItem]
    total: int
    limit: int
    offset: int


class FollowingItem(BaseModel):
    id: int
    username_display: str
    first_name: str
    last_name: str | None = None
    logo: str | None = None
    status: FollowStatus | None = None

    model_config = {'from_attributes': True}


class FollowingResponse(BaseModel):
    following: list[FollowingItem]
    total: int
    limit: int
    offset: int


class FollowRequestUserBrief(BaseModel):
    id: int
    username_display: str
    first_name: str
    last_name: str | None = None
    logo: str | None = None

    model_config = {'from_attributes': True}


class FollowRequestItem(BaseModel):
    id: int
    follower: FollowRequestUserBrief
    created_at: datetime

    model_config = {'from_attributes': True}


class FollowRequestsResponse(BaseModel):
    requests: list[FollowRequestItem]
    total: int
    limit: int
    offset: int
