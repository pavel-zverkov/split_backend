from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth.auth_service import get_current_user_optional
from ..user.user_model import User
from ..enums.event_format import EventFormat
from ..enums.event_status import EventStatus
from ..enums.privacy import Privacy
from ..enums.sport_kind import SportKind
from ..event import event_crud
from .feed_schema import (
    FeedCompetitionItem,
    FeedEventBrief,
    FeedItem,
    FeedResponse,
)

feed_router = APIRouter(prefix='/api/feed', tags=['feed'])


def _build_event_brief(db: Session, event) -> FeedEventBrief:
    return FeedEventBrief(
        id=event.id,
        name=event.name,
        logo=event.logo,
        sport_kind=event.sport_kind,
        status=event.status,
        location=event.location,
        participants_count=event_crud.get_participants_count(db, event.id),
    )


def _build_feed_items(db: Session, events) -> list[FeedItem]:
    raw = []

    for event in events:
        event_brief = _build_event_brief(db, event)

        if event.event_format == EventFormat.SINGLE:
            comp = event_crud.get_single_event_competition(db, event.id)
            comp_item = None
            if comp:
                from ..competition import competition_crud
                from ..competition.distance_model import Distance
                reg_count = competition_crud.get_registrations_count(db, comp.id)
                dist_count = db.query(Distance).filter(Distance.competition_id == comp.id).count()
                comp_item = FeedCompetitionItem(
                    id=comp.id,
                    name=comp.name,
                    date=comp.date,
                    status=comp.status,
                    registrations_count=reg_count,
                    distances_count=dist_count,
                )
            raw.append({
                "date": event.start_date,
                "type": "single",
                "event": event_brief,
                "comp": comp_item,
                "event_id": event.id,
            })
        else:
            comps = event_crud.get_competitions_brief(db, event.id)
            for comp in comps:
                raw.append({
                    "date": comp["date"],
                    "type": "multi",
                    "event_id": event.id,
                    "event": event_brief,
                    "comp": FeedCompetitionItem(**comp),
                })

    raw.sort(key=lambda x: x["date"])

    feed_items = []
    i = 0
    while i < len(raw):
        item = raw[i]
        if item["type"] == "single":
            feed_items.append(FeedItem(
                type="single",
                event=item["event"],
                date=item["date"],
                competition=item["comp"],
            ))
            i += 1
        else:
            group = [item]
            j = i + 1
            while j < len(raw) and raw[j]["type"] == "multi" and raw[j]["event_id"] == item["event_id"]:
                group.append(raw[j])
                j += 1
            feed_items.append(FeedItem(
                type="multi_stage_group",
                event=item["event"],
                date=group[0]["date"],
                competitions=[g["comp"] for g in group],
            ))
            i = j

    return feed_items


@feed_router.get('', response_model=FeedResponse)
async def get_feed(
    q: str | None = Query(None, description='Search query'),
    sport_kind: SportKind | None = Query(None, description='Filter by sport kind'),
    event_status: EventStatus | None = Query(None, alias='status', description='Filter by status'),
    privacy: Privacy | None = Query(None, description='Filter by privacy'),
    start_date_from: date | None = Query(None, description='Start date from'),
    start_date_to: date | None = Query(None, description='Start date to'),
    my_events: bool | None = Query(None, description='Only return events where current user is organizer or participant'),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    current_user_id = current_user.id if current_user else None

    events, _ = event_crud.search_events(
        db,
        query=q,
        sport_kind=sport_kind,
        status=event_status,
        privacy=privacy,
        start_date_from=start_date_from,
        start_date_to=start_date_to,
        current_user_id=current_user_id,
        my_events=bool(my_events),
        limit=1000,
        offset=0,
    )

    feed_items = _build_feed_items(db, events)
    total = len(feed_items)
    paginated = feed_items[offset:offset + limit]

    return FeedResponse(
        items=paginated,
        total=total,
        limit=limit,
        offset=offset,
    )
