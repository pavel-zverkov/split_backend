from datetime import date, datetime, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..enums.event_status import EventStatus
from ..enums.event_format import EventFormat
from ..enums.event_role import EventRole
from ..enums.event_position import EventPosition
from ..enums.participation_status import ParticipationStatus
from ..enums.privacy import Privacy
from ..enums.sport_kind import SportKind
from .event_model import Event
from .event_participation_model import EventParticipation
from .event_schema import EventCreate, EventUpdate


# Team roles (not participant/spectator)
TEAM_ROLES = [EventRole.ORGANIZER, EventRole.SECRETARY, EventRole.JUDGE, EventRole.VOLUNTEER]


def get_event_by_id(db: Session, event_id: int) -> Event | None:
    return db.query(Event).filter(Event.id == event_id).first()


# Alias for backwards compatibility
get_event = get_event_by_id


def get_event_by_name(db: Session, event_name: str, sport_kind: str) -> Event | None:
    return db.query(Event).filter(
        Event.name == event_name,
        Event.sport_kind == sport_kind
    ).first()


def create_event(db: Session, data: EventCreate, organizer_id: int) -> Event:
    event = Event(
        name=data.name,
        logo=data.logo,
        description=data.description,
        start_date=data.start_date,
        end_date=data.end_date,
        location=data.location,
        sport_kind=data.sport_kind,
        event_format=data.event_format,
        privacy=data.privacy,
        status=data.status,
        max_participants=data.max_participants,
        organizer_id=organizer_id,
    )
    db.add(event)
    db.flush()

    # Create organizer participation as chief
    participation = EventParticipation(
        user_id=organizer_id,
        event_id=event.id,
        role=EventRole.ORGANIZER,
        position=EventPosition.CHIEF,
        status=ParticipationStatus.APPROVED,
        joined_at=datetime.now(timezone.utc),
    )
    db.add(participation)
    db.commit()
    db.refresh(event)
    return event


def update_event(db: Session, event: Event, data: EventUpdate) -> Event:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)
    db.commit()
    db.refresh(event)
    return event


def delete_event(db: Session, event: Event) -> None:
    # Delete all participations first (due to foreign key constraint)
    db.query(EventParticipation).filter(EventParticipation.event_id == event.id).delete()
    db.delete(event)
    db.commit()


def finish_event_competitions(db: Session, event_id: int) -> None:
    """Auto-transition all child competitions when event is finished."""
    from ..competition.competition_model import Competition
    from ..enums.competition_status import CompetitionStatus

    competitions = db.query(Competition).filter(
        Competition.event_id == event_id,
        Competition.status.notin_([CompetitionStatus.FINISHED, CompetitionStatus.CANCELLED])
    ).all()

    for comp in competitions:
        if comp.status == CompetitionStatus.IN_PROGRESS:
            comp.status = CompetitionStatus.FINISHED
        else:
            comp.status = CompetitionStatus.CANCELLED


def has_open_registration(db: Session, event_id: int) -> bool:
    """Check if any competition in the event has registration open."""
    from ..competition.competition_model import Competition
    from ..enums.competition_status import CompetitionStatus

    return db.query(Competition).filter(
        Competition.event_id == event_id,
        Competition.status == CompetitionStatus.REGISTRATION_OPEN
    ).count() > 0


def get_competitions_count(db: Session, event_id: int) -> int:
    from ..competition.competition_model import Competition
    return db.query(Competition).filter(Competition.event_id == event_id).count()


def get_team_count(db: Session, event_id: int) -> int:
    """Count team members (organizer, secretary, judge, volunteer)."""
    return db.query(EventParticipation).filter(
        EventParticipation.event_id == event_id,
        EventParticipation.role.in_(TEAM_ROLES),
        EventParticipation.status == ParticipationStatus.APPROVED
    ).count()


def get_participants_count(db: Session, event_id: int) -> int:
    """Count participants (athletes)."""
    return db.query(EventParticipation).filter(
        EventParticipation.event_id == event_id,
        EventParticipation.role == EventRole.PARTICIPANT,
        EventParticipation.status == ParticipationStatus.APPROVED
    ).count()


def get_participation(db: Session, user_id: int, event_id: int) -> EventParticipation | None:
    return db.query(EventParticipation).filter(
        EventParticipation.user_id == user_id,
        EventParticipation.event_id == event_id
    ).first()


def get_participation_by_id(db: Session, participation_id: int) -> EventParticipation | None:
    return db.query(EventParticipation).filter(
        EventParticipation.id == participation_id
    ).first()


def is_team_member(db: Session, user_id: int, event_id: int) -> bool:
    """Check if user is a team member (not participant/spectator)."""
    participation = get_participation(db, user_id, event_id)
    if not participation or participation.status != ParticipationStatus.APPROVED:
        return False
    return participation.role in TEAM_ROLES


def is_organizer(db: Session, user_id: int, event_id: int) -> bool:
    """Check if user is an organizer (chief or deputy)."""
    participation = get_participation(db, user_id, event_id)
    if not participation or participation.status != ParticipationStatus.APPROVED:
        return False
    return participation.role == EventRole.ORGANIZER


def is_chief_organizer(db: Session, user_id: int, event_id: int) -> bool:
    """Check if user is the chief organizer."""
    participation = get_participation(db, user_id, event_id)
    if not participation or participation.status != ParticipationStatus.APPROVED:
        return False
    return participation.role == EventRole.ORGANIZER and participation.position == EventPosition.CHIEF


def is_chief_secretary(db: Session, user_id: int, event_id: int) -> bool:
    """Check if user is the chief secretary."""
    participation = get_participation(db, user_id, event_id)
    if not participation or participation.status != ParticipationStatus.APPROVED:
        return False
    return participation.role == EventRole.SECRETARY and participation.position == EventPosition.CHIEF


def can_update_event(db: Session, user_id: int, event_id: int) -> bool:
    """Check if user can update event (organizer or chief secretary)."""
    return is_organizer(db, user_id, event_id) or is_chief_secretary(db, user_id, event_id)


def search_events(
    db: Session,
    query: str | None = None,
    sport_kind: SportKind | None = None,
    status: EventStatus | None = None,
    privacy: Privacy | None = None,
    start_date_from: date | None = None,
    start_date_to: date | None = None,
    current_user_id: int | None = None,
    my_events: bool = False,
    limit: int = 20,
    offset: int = 0
) -> tuple[list[Event], int]:
    q = db.query(Event)

    # Filter by sport_kind
    if sport_kind:
        q = q.filter(Event.sport_kind == sport_kind)

    # Filter by status
    if status:
        q = q.filter(Event.status == status)
    else:
        # Exclude draft events unless user is a team member
        if current_user_id:
            team_event_ids = db.query(EventParticipation.event_id).filter(
                EventParticipation.user_id == current_user_id,
                EventParticipation.role.in_(TEAM_ROLES),
                EventParticipation.status == ParticipationStatus.APPROVED
            ).subquery()
            q = q.filter(
                or_(
                    Event.status != EventStatus.DRAFT,
                    Event.id.in_(team_event_ids)
                )
            )
        else:
            q = q.filter(Event.status != EventStatus.DRAFT)

    # Filter by privacy
    if privacy:
        q = q.filter(Event.privacy == privacy)

    # Filter to events where current user is organizer or participant
    if my_events and current_user_id:
        my_event_ids = db.query(EventParticipation.event_id).filter(
            EventParticipation.user_id == current_user_id,
            EventParticipation.role.in_([EventRole.ORGANIZER, EventRole.PARTICIPANT]),
            EventParticipation.status == ParticipationStatus.APPROVED,
        ).subquery()
        q = q.filter(Event.id.in_(my_event_ids))

    # Filter by date range
    if start_date_from:
        q = q.filter(Event.start_date >= start_date_from)
    if start_date_to:
        q = q.filter(Event.start_date <= start_date_to)

    # Search by query
    if query:
        search_pattern = f'%{query}%'
        q = q.filter(
            or_(
                Event.name.ilike(search_pattern),
                Event.description.ilike(search_pattern),
                Event.location.ilike(search_pattern),
            )
        )

    total = q.count()
    events = q.order_by(Event.start_date.asc(), Event.end_date.asc()).offset(offset).limit(limit).all()
    return events, total


def get_team_members(
    db: Session,
    event_id: int,
    role: EventRole | None = None,
    limit: int = 20,
    offset: int = 0
) -> tuple[list[EventParticipation], int]:
    """Get team members (organizer, secretary, judge, volunteer)."""
    q = db.query(EventParticipation).filter(
        EventParticipation.event_id == event_id,
        EventParticipation.role.in_(TEAM_ROLES),
        EventParticipation.status == ParticipationStatus.APPROVED
    )

    if role:
        q = q.filter(EventParticipation.role == role)

    total = q.count()
    members = q.offset(offset).limit(limit).all()
    return members, total


def get_chief_for_role(db: Session, event_id: int, role: EventRole) -> EventParticipation | None:
    """Get the chief for a specific role."""
    return db.query(EventParticipation).filter(
        EventParticipation.event_id == event_id,
        EventParticipation.role == role,
        EventParticipation.position == EventPosition.CHIEF,
        EventParticipation.status == ParticipationStatus.APPROVED
    ).first()


def create_team_member(
    db: Session,
    user_id: int,
    event_id: int,
    role: EventRole,
    position: EventPosition | None = None
) -> EventParticipation:
    participation = EventParticipation(
        user_id=user_id,
        event_id=event_id,
        role=role,
        position=position,
        status=ParticipationStatus.APPROVED,
        joined_at=datetime.now(timezone.utc),
    )
    db.add(participation)
    db.commit()
    db.refresh(participation)
    return participation


def update_team_member(
    db: Session,
    participation: EventParticipation,
    role: EventRole | None = None,
    position: EventPosition | None = None
) -> EventParticipation:
    if role is not None:
        participation.role = role
    if position is not None:
        participation.position = position
    db.commit()
    db.refresh(participation)
    return participation


def delete_participation(db: Session, participation: EventParticipation) -> None:
    db.delete(participation)
    db.commit()


def transfer_ownership(
    db: Session,
    event: Event,
    old_organizer: EventParticipation,
    new_organizer: EventParticipation
) -> Event:
    # Old organizer becomes deputy
    old_organizer.position = EventPosition.DEPUTY
    # New organizer becomes chief organizer
    new_organizer.role = EventRole.ORGANIZER
    new_organizer.position = EventPosition.CHIEF
    # Update event organizer_id
    event.organizer_id = new_organizer.user_id
    db.commit()
    db.refresh(event)
    return event


# Status transition rules
VALID_STATUS_TRANSITIONS = {
    EventStatus.DRAFT: [EventStatus.PLANNED, EventStatus.CANCELLED],
    EventStatus.PLANNED: [EventStatus.DRAFT, EventStatus.IN_PROGRESS, EventStatus.CANCELLED],
    EventStatus.IN_PROGRESS: [EventStatus.FINISHED, EventStatus.CANCELLED],
    EventStatus.FINISHED: [],
    EventStatus.CANCELLED: [],
}


def is_valid_status_transition(current: EventStatus, new: EventStatus) -> bool:
    """Check if status transition is valid."""
    if current == new:
        return True
    return new in VALID_STATUS_TRANSITIONS.get(current, [])


# ===== Participation Functions =====

def create_participation(
    db: Session,
    user_id: int,
    event_id: int,
    role: EventRole,
    position: EventPosition | None = None,
    status: ParticipationStatus = ParticipationStatus.PENDING
) -> EventParticipation:
    """Create a new event participation."""
    participation = EventParticipation(
        user_id=user_id,
        event_id=event_id,
        role=role,
        position=position,
        status=status,
        joined_at=datetime.now(timezone.utc) if status == ParticipationStatus.APPROVED else None,
    )
    db.add(participation)
    db.commit()
    db.refresh(participation)
    return participation


def update_participation_status(
    db: Session,
    participation: EventParticipation,
    status: ParticipationStatus
) -> EventParticipation:
    """Update participation status."""
    participation.status = status
    if status == ParticipationStatus.APPROVED:
        participation.joined_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(participation)
    return participation


def get_participants(
    db: Session,
    event_id: int,
    status: ParticipationStatus | None = None,
    limit: int = 20,
    offset: int = 0
) -> tuple[list[EventParticipation], int]:
    """Get participants (athlete role only)."""
    q = db.query(EventParticipation).filter(
        EventParticipation.event_id == event_id,
        EventParticipation.role == EventRole.PARTICIPANT
    )

    if status:
        q = q.filter(EventParticipation.status == status)

    total = q.count()
    participants = q.offset(offset).limit(limit).all()
    return participants, total


def get_participation_requests(
    db: Session,
    event_id: int,
    status: ParticipationStatus = ParticipationStatus.PENDING,
    role: EventRole | None = None,
    limit: int = 20,
    offset: int = 0
) -> tuple[list[EventParticipation], int]:
    """Get pending or rejected participation requests."""
    q = db.query(EventParticipation).filter(
        EventParticipation.event_id == event_id,
        EventParticipation.status == status
    )

    if role:
        q = q.filter(EventParticipation.role == role)

    total = q.count()
    requests = q.order_by(EventParticipation.created_at.desc()).offset(offset).limit(limit).all()
    return requests, total


def get_active_invites(db: Session, event_id: int) -> list:
    """Get active (not expired, not fully used) invites."""
    from .event_invite_model import EventInvite

    now = datetime.now(timezone.utc)
    q = db.query(EventInvite).filter(
        EventInvite.event_id == event_id
    )

    # Filter out expired
    q = q.filter(
        or_(
            EventInvite.expires_at.is_(None),
            EventInvite.expires_at > now
        )
    )

    # Filter out fully used (where max_uses is set and uses_count >= max_uses)
    invites = q.all()
    active = [
        inv for inv in invites
        if inv.max_uses is None or inv.uses_count < inv.max_uses
    ]

    return active


def validate_event_for_planned(db: Session, event: Event) -> str | None:
    """Validate event can transition to PLANNED. Returns error message or None."""
    comps_count = get_competitions_count(db, event.id)
    if event.event_format == EventFormat.SINGLE:
        if comps_count != 1:
            return 'Single-format event must have exactly 1 competition'
    else:
        if comps_count < 2:
            return 'Multi-stage event must have at least 2 competitions to be published'
    return None


def validate_event_for_in_progress(event: Event) -> str | None:
    """Validate event can transition to IN_PROGRESS. Returns error message or None."""
    today = date.today()
    if today < event.start_date:
        return f'Cannot start event before start date ({event.start_date})'
    return None


def validate_event_for_finished(db: Session, event: Event) -> str | None:
    """Validate event can transition to FINISHED. Returns error message or None."""
    from ..competition.competition_model import Competition
    from ..enums.competition_status import CompetitionStatus

    today = date.today()

    # Allow finish if end_date has passed
    if today > event.end_date:
        return None

    # Otherwise all competitions must be finished or cancelled
    unfinished = db.query(Competition).filter(
        Competition.event_id == event.id,
        Competition.status.notin_([CompetitionStatus.FINISHED, CompetitionStatus.CANCELLED])
    ).count()

    if unfinished > 0:
        return f'Cannot finish event: {unfinished} competition(s) are not finished or cancelled'

    return None


def get_competitions_brief(db: Session, event_id: int) -> list[dict]:
    """Get brief competition info for an event (used in list/detail responses)."""
    from ..competition.competition_model import Competition
    from ..competition.competition_registration_model import CompetitionRegistration
    from ..competition.distance_model import Distance

    competitions = db.query(Competition).filter(
        Competition.event_id == event_id
    ).order_by(Competition.date.asc()).all()

    result = []
    for comp in competitions:
        reg_count = db.query(CompetitionRegistration).filter(
            CompetitionRegistration.competition_id == comp.id
        ).count()
        dist_count = db.query(Distance).filter(
            Distance.competition_id == comp.id
        ).count()
        result.append({
            "id": comp.id,
            "name": comp.name,
            "date": comp.date,
            "status": comp.status,
            "registrations_count": reg_count,
            "distances_count": dist_count,
        })
    return result


def get_single_event_competition(db: Session, event_id: int):
    """Get the single competition for a single-format event."""
    from ..competition.competition_model import Competition
    return db.query(Competition).filter(Competition.event_id == event_id).first()


def sync_single_event_competition_status(
    db: Session,
    event: Event,
    old_status: EventStatus,
    new_status: EventStatus
) -> None:
    """Auto-sync competition status when single-format event status changes."""
    if event.event_format != EventFormat.SINGLE:
        return

    from ..competition.competition_model import Competition
    from ..enums.competition_status import CompetitionStatus

    comp = db.query(Competition).filter(Competition.event_id == event.id).first()
    if not comp:
        return

    if old_status == EventStatus.DRAFT and new_status == EventStatus.PLANNED:
        comp.status = CompetitionStatus.REGISTRATION_OPEN
    elif old_status == EventStatus.PLANNED and new_status == EventStatus.IN_PROGRESS:
        comp.status = CompetitionStatus.IN_PROGRESS
    elif old_status == EventStatus.IN_PROGRESS and new_status == EventStatus.FINISHED:
        comp.status = CompetitionStatus.FINISHED
    elif new_status == EventStatus.CANCELLED:
        comp.status = CompetitionStatus.CANCELLED

    db.flush()
