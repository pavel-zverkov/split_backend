from pydantic import BaseModel


class UserResult(BaseModel):
    id: int
    username_display: str
    first_name: str
    last_name: str | None = None
    logo: str | None = None
    account_type: str


class EventResult(BaseModel):
    id: int
    name: str
    start_date: str
    end_date: str
    location: str | None = None
    sport_kind: str | None = None
    status: str


class ClubResult(BaseModel):
    id: int
    name: str
    location: str | None = None
    logo: str | None = None


class EventBrief(BaseModel):
    id: int
    name: str


class CompetitionResult(BaseModel):
    id: int
    name: str
    date: str
    location: str | None = None
    sport_kind: str | None = None
    status: str
    event: EventBrief


class GlobalSearchResponse(BaseModel):
    query: str
    users: list[UserResult]
    events: list[EventResult]
    clubs: list[ClubResult]
    competitions: list[CompetitionResult]
