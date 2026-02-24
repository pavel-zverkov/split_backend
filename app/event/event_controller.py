from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth.auth_service import get_current_user, get_current_user_optional
from ..user.user_model import User
from ..user import user_crud
from ..enums.event_status import EventStatus
from ..enums.event_format import EventFormat
from ..enums.event_role import EventRole
from ..enums.event_position import EventPosition
from ..enums.privacy import Privacy
from ..enums.sport_kind import SportKind
from . import event_crud
from .event_schema import (
    CompetitionBriefForList,
    EventCreate,
    EventUpdate,
    EventResponse,
    EventDetailResponse,
    EventListItem,
    EventListResponse,
    EventOrganizerBrief,
    SingleEventCompetitionBrief,
    TeamMemberItem,
    TeamMemberUserBrief,
    TeamListResponse,
    AddTeamMemberRequest,
    TeamMemberResponse,
    UpdateTeamMemberRequest,
    TransferOwnershipRequest,
    TransferOwnershipResponse,
    EventLogoResponse,
)

event_router = APIRouter(prefix='/api/events', tags=['events'])


def _build_competition_brief(db: Session, event) -> SingleEventCompetitionBrief | None:
    """Build competition brief for single-format events."""
    if event.event_format != EventFormat.SINGLE:
        return None
    comp = event_crud.get_single_event_competition(db, event.id)
    if not comp:
        return None
    from ..competition import competition_crud
    return SingleEventCompetitionBrief(
        id=comp.id,
        start_format=comp.start_format,
        registrations_count=competition_crud.get_registrations_count(db, comp.id),
    )


def _build_competitions_list(db: Session, event) -> list[CompetitionBriefForList]:
    """Build competitions list for multi-stage events."""
    if event.event_format != EventFormat.MULTI_STAGE:
        return []
    briefs = event_crud.get_competitions_brief(db, event.id)
    return [CompetitionBriefForList(**b) for b in briefs]


@event_router.post('', response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    data: EventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new event. Creator becomes chief organizer."""
    # Validate status - only draft or planned allowed at creation
    if data.status not in [EventStatus.DRAFT, EventStatus.PLANNED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Status must be draft or planned at creation'
        )

    # Validate dates
    if data.end_date < data.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='End date must be equal to or after start date'
        )

    # Check for duplicate (name + sport_kind must be unique)
    existing = event_crud.get_event_by_name(db, data.name, data.sport_kind)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Event with this name and sport kind already exists'
        )

    event = event_crud.create_event(db, data, current_user.id)

    # For single-format events, auto-create the competition
    competition_brief = None
    competitions_count = 0
    if data.event_format == EventFormat.SINGLE:
        from ..competition.competition_model import Competition
        from ..enums.start_format import StartFormat
        from ..enums.competition_status import CompetitionStatus

        comp_data = data.competition
        comp = Competition(
            event_id=event.id,
            name=event.name,
            description=comp_data.description if comp_data else None,
            date=event.start_date,
            sport_kind=event.sport_kind,
            start_format=comp_data.start_format if comp_data else StartFormat.SEPARATED_START,
            location=comp_data.location if comp_data else event.location,
            status=CompetitionStatus.PLANNED,
        )
        db.add(comp)
        db.commit()
        db.refresh(comp)
        competitions_count = 1
        competition_brief = SingleEventCompetitionBrief(
            id=comp.id,
            start_format=comp.start_format,
            registrations_count=0,
        )

    return EventResponse(
        id=event.id,
        name=event.name,
        logo=event.logo,
        description=event.description,
        start_date=event.start_date,
        end_date=event.end_date,
        location=event.location,
        sport_kind=event.sport_kind,
        event_format=event.event_format,
        privacy=event.privacy,
        status=event.status,
        max_participants=event.max_participants,
        organizer_id=event.organizer_id,
        competitions_count=competitions_count,
        team_count=1,
        participants_count=0,
        has_open_registration=False,
        recruitment_open=event.recruitment_open,
        needed_roles=event.needed_roles,
        competition_brief=competition_brief,
        created_at=event.created_at,
    )


@event_router.get('/{event_id}', response_model=EventDetailResponse)
async def get_event(
    event_id: int,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Get event details."""
    event = event_crud.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Event not found'
        )

    # Check visibility for draft events
    if event.status == EventStatus.DRAFT:
        if not current_user or not event_crud.is_team_member(db, current_user.id, event_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Event not found'
            )

    competitions_count = event_crud.get_competitions_count(db, event_id)
    team_count = event_crud.get_team_count(db, event_id)
    participants_count = event_crud.get_participants_count(db, event_id)

    # Get user's role if authenticated
    my_role = None
    my_position = None
    if current_user:
        participation = event_crud.get_participation(db, current_user.id, event_id)
        if participation and participation.status.value == 'approved':
            my_role = participation.role
            my_position = participation.position

    return EventDetailResponse(
        id=event.id,
        name=event.name,
        logo=event.logo,
        description=event.description,
        start_date=event.start_date,
        end_date=event.end_date,
        location=event.location,
        sport_kind=event.sport_kind,
        event_format=event.event_format,
        privacy=event.privacy,
        status=event.status,
        max_participants=event.max_participants,
        organizer=EventOrganizerBrief(
            id=event.organizer.id,
            username_display=event.organizer.username_display,
            first_name=event.organizer.first_name,
        ),
        competitions_count=competitions_count,
        participants_count=participants_count,
        team_count=team_count,
        my_role=my_role,
        my_position=my_position,
        has_open_registration=event_crud.has_open_registration(db, event_id),
        recruitment_open=event.recruitment_open,
        needed_roles=event.needed_roles,
        competition_brief=_build_competition_brief(db, event),
        competitions=_build_competitions_list(db, event),
        created_at=event.created_at,
    )


@event_router.get('', response_model=EventListResponse)
async def list_events(
    q: str | None = Query(None, description='Search query'),
    sport_kind: SportKind | None = Query(None, description='Filter by sport kind'),
    event_status: EventStatus | None = Query(None, alias='status', description='Filter by status'),
    privacy: Privacy | None = Query(None, description='Filter by privacy'),
    start_date_from: date | None = Query(None, description='Start date from'),
    start_date_to: date | None = Query(None, description='Start date to'),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """List and search events."""
    current_user_id = current_user.id if current_user else None
    events, total = event_crud.search_events(
        db,
        query=q,
        sport_kind=sport_kind,
        status=event_status,
        privacy=privacy,
        start_date_from=start_date_from,
        start_date_to=start_date_to,
        current_user_id=current_user_id,
        limit=limit,
        offset=offset
    )

    event_items = []
    for event in events:
        competitions_count = event_crud.get_competitions_count(db, event.id)
        participants_count = event_crud.get_participants_count(db, event.id)

        my_role = None
        if current_user:
            participation = event_crud.get_participation(db, current_user.id, event.id)
            if participation and participation.status.value == 'approved':
                my_role = participation.role

        event_items.append(EventListItem(
            id=event.id,
            name=event.name,
            logo=event.logo,
            start_date=event.start_date,
            end_date=event.end_date,
            location=event.location,
            sport_kind=event.sport_kind,
            event_format=event.event_format,
            privacy=event.privacy,
            status=event.status,
            competitions_count=competitions_count,
            participants_count=participants_count,
            my_role=my_role,
            has_open_registration=event_crud.has_open_registration(db, event.id),
            recruitment_open=event.recruitment_open,
            needed_roles=event.needed_roles,
            competition_brief=_build_competition_brief(db, event),
            competitions=_build_competitions_list(db, event),
        ))

    return EventListResponse(
        events=event_items,
        total=total,
        limit=limit,
        offset=offset,
    )


@event_router.patch('/{event_id}', response_model=EventDetailResponse)
async def update_event(
    event_id: int,
    data: EventUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update event. Only organizer or chief secretary can update."""
    event = event_crud.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Event not found'
        )

    # Check permissions
    if not event_crud.can_update_event(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer or chief secretary can update event'
        )

    # Validate status transition
    if data.status and not event_crud.is_valid_status_transition(event.status, data.status):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid status transition from {event.status.value} to {data.status.value}'
        )

    # Validate DRAFT → PLANNED transition
    if data.status == EventStatus.PLANNED and event.status == EventStatus.DRAFT:
        error = event_crud.validate_event_for_planned(db, event)
        if error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )

    # Validate → IN_PROGRESS transition
    if data.status == EventStatus.IN_PROGRESS and event.status != EventStatus.IN_PROGRESS:
        error = event_crud.validate_event_for_in_progress(event)
        if error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )

    # Validate → FINISHED transition
    if data.status == EventStatus.FINISHED and event.status != EventStatus.FINISHED:
        error = event_crud.validate_event_for_finished(db, event)
        if error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )

    old_status = event.status
    updated_event = event_crud.update_event(db, event, data)

    # Sync single-event competition status
    if data.status and data.status != old_status:
        event_crud.sync_single_event_competition_status(db, updated_event, old_status, data.status)

    # FINISHED cascade: auto-transition all child competitions (for multi_stage)
    if data.status == EventStatus.FINISHED:
        event_crud.finish_event_competitions(db, event_id)
        db.commit()

    competitions_count = event_crud.get_competitions_count(db, event_id)
    team_count = event_crud.get_team_count(db, event_id)
    participants_count = event_crud.get_participants_count(db, event_id)

    participation = event_crud.get_participation(db, current_user.id, event_id)

    return EventDetailResponse(
        id=updated_event.id,
        name=updated_event.name,
        logo=updated_event.logo,
        description=updated_event.description,
        start_date=updated_event.start_date,
        end_date=updated_event.end_date,
        location=updated_event.location,
        sport_kind=updated_event.sport_kind,
        event_format=updated_event.event_format,
        privacy=updated_event.privacy,
        status=updated_event.status,
        max_participants=updated_event.max_participants,
        organizer=EventOrganizerBrief(
            id=updated_event.organizer.id,
            username_display=updated_event.organizer.username_display,
            first_name=updated_event.organizer.first_name,
        ),
        competitions_count=competitions_count,
        participants_count=participants_count,
        team_count=team_count,
        my_role=participation.role if participation else None,
        my_position=participation.position if participation else None,
        has_open_registration=event_crud.has_open_registration(db, event_id),
        recruitment_open=updated_event.recruitment_open,
        needed_roles=updated_event.needed_roles,
        competition_brief=_build_competition_brief(db, updated_event),
        competitions=_build_competitions_list(db, updated_event),
        created_at=updated_event.created_at,
    )


@event_router.delete('/{event_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete event. Only chief organizer can delete."""
    event = event_crud.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Event not found'
        )

    # Only chief organizer can delete
    if not event_crud.is_chief_organizer(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only chief organizer can delete event'
        )

    # Cannot delete if in progress
    if event.status == EventStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Cannot delete event in progress'
        )

    event_crud.delete_event(db, event)
    return None


@event_router.post('/{event_id}/logo', response_model=EventLogoResponse)
async def upload_event_logo(
    event_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload event logo. Only organizer or chief secretary can upload."""
    event = event_crud.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Event not found'
        )

    if not event_crud.can_update_event(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer or chief secretary can upload logo'
        )

    allowed_types = ['image/jpeg', 'image/png', 'image/webp']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='File must be JPEG, PNG, or WebP image'
        )

    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='File size must be less than 5MB'
        )

    from ..database.minio_service import upload_event_logo
    logo_url = upload_event_logo(event_id, contents, file.content_type)
    event.logo = logo_url
    db.commit()

    return EventLogoResponse(logo=logo_url)


@event_router.get('/{event_id}/team', response_model=TeamListResponse)
async def get_team_members(
    event_id: int,
    role: EventRole | None = Query(None, description='Filter by role'),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """List event team members."""
    event = event_crud.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Event not found'
        )

    # Check visibility for draft events
    if event.status == EventStatus.DRAFT:
        if not current_user or not event_crud.is_team_member(db, current_user.id, event_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Event not found'
            )

    # Validate role is a team role
    if role and role not in event_crud.TEAM_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid team role. Use participant/spectator endpoints for athletes.'
        )

    members, total = event_crud.get_team_members(db, event_id, role=role, limit=limit, offset=offset)

    team_items = []
    for m in members:
        user = m.user
        team_items.append(TeamMemberItem(
            id=m.id,
            user=TeamMemberUserBrief(
                id=user.id,
                username_display=user.username_display,
                first_name=user.first_name,
                last_name=f"{user.last_name[0]}." if user.last_name else None,
                logo=user.logo,
            ),
            role=m.role,
            position=m.position,
            joined_at=m.joined_at,
        ))

    return TeamListResponse(
        team=team_items,
        total=total,
        limit=limit,
        offset=offset,
    )


@event_router.post('/{event_id}/team', response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_team_member(
    event_id: int,
    data: AddTeamMemberRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a team member to event."""
    event = event_crud.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Event not found'
        )

    # Only organizer can add team members
    if not event_crud.is_organizer(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer can add team members'
        )

    # Validate role is a team role
    if data.role not in event_crud.TEAM_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid team role. Use participant/spectator endpoints for athletes.'
        )

    # Check user exists
    target_user = user_crud.get_user_by_id(db, data.user_id)
    if not target_user or not target_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found'
        )

    # Check if already a team member
    existing = event_crud.get_participation(db, data.user_id, event_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='User is already a participant in this event'
        )

    # Check if chief already exists for this role
    if data.position == EventPosition.CHIEF:
        existing_chief = event_crud.get_chief_for_role(db, event_id, data.role)
        if existing_chief:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Chief already exists for role {data.role.value}'
            )

    participation = event_crud.create_team_member(db, data.user_id, event_id, data.role, data.position)

    return TeamMemberResponse(
        id=participation.id,
        user_id=participation.user_id,
        event_id=participation.event_id,
        role=participation.role,
        position=participation.position,
        status=participation.status,
        joined_at=participation.joined_at,
    )


@event_router.patch('/{event_id}/team/{user_id}', response_model=TeamMemberResponse)
async def update_team_member(
    event_id: int,
    user_id: int,
    data: UpdateTeamMemberRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a team member's role or position."""
    event = event_crud.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Event not found'
        )

    # Only organizer can update team members
    if not event_crud.is_organizer(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer can update team members'
        )

    participation = event_crud.get_participation(db, user_id, event_id)
    if not participation or participation.role not in event_crud.TEAM_ROLES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Team member not found'
        )

    # Cannot change chief organizer's role
    if participation.role == EventRole.ORGANIZER and participation.position == EventPosition.CHIEF:
        if data.role and data.role != EventRole.ORGANIZER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Cannot change chief organizer role. Use transfer ownership.'
            )

    # Validate new role is a team role
    if data.role and data.role not in event_crud.TEAM_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid team role'
        )

    # Check if chief already exists for target role
    target_role = data.role or participation.role
    if data.position == EventPosition.CHIEF:
        existing_chief = event_crud.get_chief_for_role(db, event_id, target_role)
        if existing_chief and existing_chief.id != participation.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Chief already exists for role {target_role.value}'
            )

    updated = event_crud.update_team_member(db, participation, data.role, data.position)

    return TeamMemberResponse(
        id=updated.id,
        user_id=updated.user_id,
        event_id=updated.event_id,
        role=updated.role,
        position=updated.position,
        status=updated.status,
        joined_at=updated.joined_at,
    )


@event_router.delete('/{event_id}/team/{user_id}', status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    event_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a team member from event."""
    event = event_crud.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Event not found'
        )

    # Only organizer can remove team members
    if not event_crud.is_organizer(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer can remove team members'
        )

    participation = event_crud.get_participation(db, user_id, event_id)
    if not participation or participation.role not in event_crud.TEAM_ROLES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Team member not found'
        )

    # Cannot remove yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Cannot remove yourself from team'
        )

    # Cannot remove chief organizer
    if participation.role == EventRole.ORGANIZER and participation.position == EventPosition.CHIEF:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Cannot remove chief organizer. Transfer ownership first.'
        )

    event_crud.delete_participation(db, participation)
    return None


@event_router.post('/{event_id}/transfer-ownership', response_model=TransferOwnershipResponse)
async def transfer_ownership(
    event_id: int,
    request: TransferOwnershipRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Transfer event ownership to another team member."""
    event = event_crud.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Event not found'
        )

    # Only chief organizer can transfer
    if not event_crud.is_chief_organizer(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only chief organizer can transfer ownership'
        )

    # Cannot transfer to self
    if request.new_organizer_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Cannot transfer ownership to yourself'
        )

    # New organizer must be a team member
    new_organizer = event_crud.get_participation(db, request.new_organizer_id, event_id)
    if not new_organizer or new_organizer.role not in event_crud.TEAM_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='New organizer must be a team member'
        )

    old_organizer = event_crud.get_participation(db, current_user.id, event_id)

    updated_event = event_crud.transfer_ownership(db, event, old_organizer, new_organizer)

    return TransferOwnershipResponse(
        id=updated_event.id,
        name=updated_event.name,
        organizer_id=updated_event.organizer_id,
        message='Ownership transferred successfully'
    )
