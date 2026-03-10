from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from . import search_crud
from .search_schema import (
    GlobalSearchResponse,
    UserResult,
    EventResult,
    ClubResult,
    CompetitionResult,
    EventBrief,
)

search_router = APIRouter(prefix='/api/search', tags=['search'])


@search_router.get('', response_model=GlobalSearchResponse)
async def global_search(
    q: str = Query(..., min_length=2, description='Search query'),
    limit: int = Query(5, ge=1, le=20, description='Max results per type'),
    db: Session = Depends(get_db),
):
    """Search across users, events, clubs, and competitions."""
    users = search_crud.search_users(db, q, limit)
    events = search_crud.search_events(db, q, limit)
    clubs = search_crud.search_clubs(db, q, limit)
    competitions = search_crud.search_competitions(db, q, limit)

    return GlobalSearchResponse(
        query=q,
        users=[
            UserResult(
                id=u.id,
                username_display=u.username_display,
                first_name=u.first_name,
                last_name=u.last_name,
                logo=u.logo,
                account_type=u.account_type.value,
            )
            for u in users
        ],
        events=[
            EventResult(
                id=e.id,
                name=e.name,
                start_date=str(e.start_date),
                end_date=str(e.end_date),
                location=e.location,
                sport_kind=e.sport_kind.value if e.sport_kind else None,
                status=e.status.value,
            )
            for e in events
        ],
        clubs=[
            ClubResult(
                id=c.id,
                name=c.name,
                location=c.location,
                logo=c.logo,
            )
            for c in clubs
        ],
        competitions=[
            CompetitionResult(
                id=c.id,
                name=c.name,
                date=str(c.date),
                location=c.location,
                sport_kind=c.sport_kind.value if c.sport_kind else None,
                status=c.status.value,
                event=EventBrief(id=c.parent_event.id, name=c.parent_event.name),
            )
            for c in competitions
        ],
    )
