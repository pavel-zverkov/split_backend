import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth.auth_service import get_current_user, get_current_user_optional
from ..user.user_model import User
from ..enums.event_status import EventStatus
from ..enums.event_role import EventRole
from ..enums.event_position import EventPosition
from ..enums.participation_status import ParticipationStatus
from ..enums.privacy import Privacy
from . import event_crud
from .event_invite_model import EventInvite
from .event_participation_model import EventParticipation
from .event_schema import (
    JoinEventRequest,
    ParticipationResponse,
    ParticipantItem,
    ParticipantUserBrief,
    ParticipantsListResponse,
    RequestItem,
    RequestsListResponse,
    UpdateRequestStatus,
    MyParticipationResponse,
    MyParticipationCompetition,
    RecruitmentSettingsUpdate,
    RecruitmentSettingsResponse,
    CreateInviteRequest,
    InviteResponse,
    InviteListItem,
    InviteCreatorBrief,
    InvitesListResponse,
    CompetitionBrief,
    AddParticipantRequest,
    BatchAddParticipantsRequest,
    BatchAddParticipantsResponse,
    BatchParticipantResultItem,
    ClubParticipantsRequest,
)
from ..user import user_crud
from ..club import club_crud

participation_router = APIRouter(prefix='/api/events', tags=['event-participation'])


# ===== Helper Functions =====

def get_event_or_404(db: Session, event_id: int):
    """Get event or raise 404."""
    event = event_crud.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Event not found'
        )
    return event


def check_registration_allowed(event):
    """Check if event allows registration."""
    if event.status not in [EventStatus.PLANNED, EventStatus.IN_PROGRESS]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Event is not open for registration'
        )


def get_invite_by_token(db: Session, token: str) -> EventInvite | None:
    """Get invite by token."""
    return db.query(EventInvite).filter(EventInvite.token == token).first()


def validate_invite(invite: EventInvite):
    """Validate invite is still usable."""
    if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invite has expired'
        )
    if invite.max_uses and invite.uses_count >= invite.max_uses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invite has reached maximum uses'
        )


def use_invite(db: Session, invite: EventInvite):
    """Increment invite usage count."""
    invite.uses_count += 1
    db.commit()


# ===== 7.1 Join Event =====

@participation_router.post('/{event_id}/join', response_model=ParticipationResponse, status_code=status.HTTP_201_CREATED)
async def join_event(
    event_id: int,
    data: JoinEventRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Join an event as participant or team member."""
    event = get_event_or_404(db, event_id)
    check_registration_allowed(event)

    # Check if already participating
    existing = event_crud.get_participation(db, current_user.id, event_id)
    if existing and existing.status in [ParticipationStatus.APPROVED, ParticipationStatus.PENDING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Already participating in this event'
        )

    # Handle invite token
    if data.token:
        invite = get_invite_by_token(db, data.token)
        if not invite or invite.event_id != event_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid invite token'
            )
        validate_invite(invite)

        # Use invite settings
        role = invite.role
        position = invite.position
        participation_status = ParticipationStatus.APPROVED
        use_invite(db, invite)
    else:
        # Self-request
        if not data.role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Role is required when not using invite token'
            )

        role = data.role
        position = None

        # Determine approval status
        if role == EventRole.PARTICIPANT:
            # Athletes
            if event.privacy == Privacy.PUBLIC:
                participation_status = ParticipationStatus.APPROVED
            else:
                participation_status = ParticipationStatus.PENDING
        elif role in event_crud.TEAM_ROLES and role != EventRole.ORGANIZER:
            # Team roles (excluding organizer which can only be added via transfer)
            if not event.recruitment_open:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Team recruitment is not open'
                )
            if event.needed_roles and role.value not in event.needed_roles:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f'Role {role.value} is not open for recruitment'
                )
            participation_status = ParticipationStatus.PENDING
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid role for self-registration'
            )

    # Delete rejected participation if exists (allow re-apply)
    if existing and existing.status == ParticipationStatus.REJECTED:
        event_crud.delete_participation(db, existing)

    # Create participation
    participation = event_crud.create_participation(
        db, current_user.id, event_id, role, position, participation_status
    )

    return ParticipationResponse(
        id=participation.id,
        user_id=participation.user_id,
        event_id=participation.event_id,
        role=participation.role,
        position=participation.position,
        status=participation.status,
        competitions=[],
        joined_at=participation.joined_at,
    )


# ===== 7.1b Add Participant (by organizer) =====

@participation_router.post('/{event_id}/participants', response_model=ParticipationResponse, status_code=status.HTTP_201_CREATED)
async def add_participant(
    event_id: int,
    data: AddParticipantRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a participant to the event. Only organizer can do this. Useful for adding ghost users."""
    event = get_event_or_404(db, event_id)

    # Only organizer or chief secretary can add participants
    if not event_crud.can_update_event(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer or chief secretary can add participants'
        )

    # Verify user exists
    target_user = user_crud.get_user_by_id(db, data.user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found'
        )

    # Check if already participating
    existing = event_crud.get_participation(db, data.user_id, event_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='User is already participating in this event'
        )

    # Cannot add chief organizer role
    if data.role == EventRole.ORGANIZER and data.position == EventPosition.CHIEF:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Cannot add chief organizer. Use transfer ownership endpoint.'
        )

    # Create participation with approved status (admin-added participants are immediately approved)
    participation = event_crud.create_participation(
        db, data.user_id, event_id, data.role, data.position, ParticipationStatus.APPROVED
    )

    return ParticipationResponse(
        id=participation.id,
        user_id=participation.user_id,
        event_id=participation.event_id,
        role=participation.role,
        position=participation.position,
        status=participation.status,
        competitions=[],
        joined_at=participation.joined_at,
    )


# ===== 7.1c Batch Add Participants =====

@participation_router.post('/{event_id}/participants/batch', response_model=BatchAddParticipantsResponse)
async def batch_add_participants(
    event_id: int,
    data: BatchAddParticipantsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Batch add participants to event with optional competition registration."""
    event = get_event_or_404(db, event_id)

    if not event_crud.can_update_event(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer or chief secretary can add participants'
        )

    results = _process_batch_participants(db, event_id, data.participants)

    return _build_batch_response(results)


# ===== 7.1d Add Participants from Club =====

@participation_router.post('/{event_id}/participants/from-club', response_model=BatchAddParticipantsResponse)
async def add_participants_from_club(
    event_id: int,
    data: ClubParticipantsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add selected club members as event participants. Requires event organizer + club admin."""
    event = get_event_or_404(db, event_id)

    if not event_crud.can_update_event(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer or chief secretary can add participants'
        )

    if not club_crud.is_club_admin(db, current_user.id, data.club_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only club owner or coach can add club members'
        )

    # Validate selected users are active club members
    from ..enums.membership_status import MembershipStatus
    results = []
    for user_id in data.user_ids:
        membership = club_crud.get_membership(db, user_id, data.club_id)
        if not membership or membership.status != MembershipStatus.ACTIVE:
            results.append(BatchParticipantResultItem(
                user_id=user_id, status='error', detail='Not an active club member'
            ))
            continue

        result = _add_single_participant(
            db, event_id, user_id, data.role, None, data.competition_ids
        )
        results.append(result)

    db.commit()
    return _build_batch_response(results)


# ===== Batch Helpers =====

def _process_batch_participants(db, event_id, participants):
    """Process a batch of participant items."""
    results = []
    for item in participants:
        result = _add_single_participant(
            db, event_id, item.user_id, item.role, item.position, item.competition_ids
        )
        results.append(result)
    db.commit()
    return results


def _add_single_participant(db, event_id, user_id, role, position, competition_ids):
    """Add a single participant and optionally register for competitions."""
    user = user_crud.get_user_by_id(db, user_id)
    if not user or not user.is_active:
        return BatchParticipantResultItem(
            user_id=user_id, status='error', detail='User not found'
        )

    existing = event_crud.get_participation(db, user_id, event_id)
    if existing:
        return BatchParticipantResultItem(
            user_id=user_id, status='skipped', detail='Already participating'
        )

    participation = EventParticipation(
        user_id=user_id,
        event_id=event_id,
        role=role,
        position=position,
        status=ParticipationStatus.APPROVED,
        joined_at=datetime.now(timezone.utc),
    )
    db.add(participation)
    db.flush()

    # Register for competitions if specified
    if competition_ids:
        from ..competition.competition_model import Competition
        from ..competition.competition_registration_model import CompetitionRegistration
        from ..enums.registration_status import RegistrationStatus
        for comp_id in competition_ids:
            comp = db.query(Competition).filter(
                Competition.id == comp_id,
                Competition.event_id == event_id
            ).first()
            if comp:
                reg = CompetitionRegistration(
                    user_id=user_id,
                    competition_id=comp_id,
                    status=RegistrationStatus.REGISTERED,
                )
                db.add(reg)

    return BatchParticipantResultItem(user_id=user_id, status='added')


def _build_batch_response(results):
    """Build batch response from results list."""
    added = sum(1 for r in results if r.status == 'added')
    skipped = sum(1 for r in results if r.status in ('skipped', 'error'))
    return BatchAddParticipantsResponse(
        added=added, skipped=skipped, results=results
    )


# ===== 7.2 List Participants =====

@participation_router.get('/{event_id}/participants', response_model=ParticipantsListResponse)
async def list_participants(
    event_id: int,
    participant_status: ParticipationStatus | None = Query(None, alias='status'),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """List event participants (athletes)."""
    event = get_event_or_404(db, event_id)

    # Check visibility
    is_team = current_user and event_crud.is_team_member(db, current_user.id, event_id)

    # Non-team members can only see approved participants
    if not is_team:
        if participant_status and participant_status != ParticipationStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Only approved participants are visible'
            )
        participant_status = ParticipationStatus.APPROVED

    participants, total = event_crud.get_participants(
        db, event_id, status=participant_status, limit=limit, offset=offset
    )

    items = []
    for p in participants:
        items.append(ParticipantItem(
            id=p.id,
            user=ParticipantUserBrief(
                id=p.user.id,
                username_display=p.user.username_display,
                first_name=p.user.first_name,
                last_name=f"{p.user.last_name[0]}." if p.user.last_name else None,
                logo=p.user.logo,
            ),
            status=p.status,
            competitions=[],
            joined_at=p.joined_at,
        ))

    return ParticipantsListResponse(
        participants=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# ===== 7.3 List Requests =====

@participation_router.get('/{event_id}/requests', response_model=RequestsListResponse)
async def list_requests(
    event_id: int,
    request_status: ParticipationStatus = Query(ParticipationStatus.PENDING, alias='status'),
    role: EventRole | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List join requests (pending or rejected)."""
    event = get_event_or_404(db, event_id)

    # Only organizer or chief secretary can view requests
    if not event_crud.can_update_event(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer or chief secretary can view requests'
        )

    requests, total = event_crud.get_participation_requests(
        db, event_id, status=request_status, role=role, limit=limit, offset=offset
    )

    items = []
    for r in requests:
        items.append(RequestItem(
            id=r.id,
            user=ParticipantUserBrief(
                id=r.user.id,
                username_display=r.user.username_display,
                first_name=r.user.first_name,
                last_name=f"{r.user.last_name[0]}." if r.user.last_name else None,
                logo=r.user.logo,
            ),
            role=r.role,
            competitions=[],
            created_at=r.created_at,
        ))

    return RequestsListResponse(
        requests=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# ===== 7.4 Approve/Reject Request =====

@participation_router.patch('/{event_id}/requests/{participation_id}', response_model=ParticipationResponse)
async def update_request_status(
    event_id: int,
    participation_id: int,
    data: UpdateRequestStatus,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Approve or reject a join request."""
    event = get_event_or_404(db, event_id)

    # Only organizer or chief secretary can update requests
    if not event_crud.can_update_event(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer or chief secretary can update requests'
        )

    participation = event_crud.get_participation_by_id(db, participation_id)
    if not participation or participation.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Request not found'
        )

    if participation.status != ParticipationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Can only update pending requests'
        )

    if data.status not in [ParticipationStatus.APPROVED, ParticipationStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Status must be approved or rejected'
        )

    updated = event_crud.update_participation_status(db, participation, data.status)

    return ParticipationResponse(
        id=updated.id,
        user_id=updated.user_id,
        event_id=updated.event_id,
        role=updated.role,
        position=updated.position,
        status=updated.status,
        competitions=[],
        joined_at=updated.joined_at,
    )


# ===== 7.5 Get My Participation =====

@participation_router.get('/{event_id}/participation/me', response_model=MyParticipationResponse)
async def get_my_participation(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's participation in event."""
    event = get_event_or_404(db, event_id)

    participation = event_crud.get_participation(db, current_user.id, event_id)
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Not participating in this event'
        )

    return MyParticipationResponse(
        id=participation.id,
        event_id=participation.event_id,
        role=participation.role,
        position=participation.position,
        status=participation.status,
        competitions=[],
        joined_at=participation.joined_at,
    )


# ===== 7.6 Leave Event =====

@participation_router.delete('/{event_id}/participation/me', status_code=status.HTTP_204_NO_CONTENT)
async def leave_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Leave an event."""
    event = get_event_or_404(db, event_id)

    participation = event_crud.get_participation(db, current_user.id, event_id)
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Not participating in this event'
        )

    # Cannot leave if chief organizer
    if participation.role == EventRole.ORGANIZER and participation.position == EventPosition.CHIEF:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Cannot leave: transfer organizer role first'
        )

    event_crud.delete_participation(db, participation)
    return None


# ===== 7.7 Update Recruitment Settings =====

@participation_router.patch('/{event_id}/recruitment', response_model=RecruitmentSettingsResponse)
async def update_recruitment(
    event_id: int,
    data: RecruitmentSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update event recruitment settings."""
    event = get_event_or_404(db, event_id)

    # Only organizer can update recruitment
    if not event_crud.is_organizer(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer can update recruitment settings'
        )

    if data.recruitment_open is not None:
        event.recruitment_open = data.recruitment_open
    if data.needed_roles is not None:
        event.needed_roles = data.needed_roles

    db.commit()
    db.refresh(event)

    return RecruitmentSettingsResponse(
        recruitment_open=event.recruitment_open,
        needed_roles=event.needed_roles,
    )


# ===== 7.8 Generate Invite Link =====

@participation_router.post('/{event_id}/invites', response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    event_id: int,
    data: CreateInviteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate an invite link for the event."""
    event = get_event_or_404(db, event_id)

    # Only organizer can create invites
    if not event_crud.is_organizer(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer can create invites'
        )

    # Generate unique token
    token = secrets.token_urlsafe(16)

    invite = EventInvite(
        event_id=event_id,
        token=token,
        role=data.role,
        position=data.position,
        competition_ids=data.competition_ids,
        expires_at=data.expires_at,
        max_uses=data.max_uses,
        uses_count=0,
        created_by=current_user.id,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    return InviteResponse(
        id=invite.id,
        token=invite.token,
        role=invite.role,
        position=invite.position,
        competition_ids=invite.competition_ids,
        expires_at=invite.expires_at,
        max_uses=invite.max_uses,
        uses_count=invite.uses_count,
        link=f"/events/{event_id}/join?token={invite.token}",
        created_at=invite.created_at,
    )


# ===== 7.9 List Active Invites =====

@participation_router.get('/{event_id}/invites', response_model=InvitesListResponse)
async def list_invites(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List active invites for the event."""
    event = get_event_or_404(db, event_id)

    # Only organizer can view invites
    if not event_crud.is_organizer(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer can view invites'
        )

    invites = event_crud.get_active_invites(db, event_id)

    items = []
    for inv in invites:
        items.append(InviteListItem(
            id=inv.id,
            token=inv.token,
            role=inv.role,
            position=inv.position,
            competition_ids=inv.competition_ids,
            expires_at=inv.expires_at,
            max_uses=inv.max_uses,
            uses_count=inv.uses_count,
            created_by=InviteCreatorBrief(
                id=inv.creator.id,
                username_display=inv.creator.username_display,
            ),
            created_at=inv.created_at,
        ))

    return InvitesListResponse(
        invites=items,
        total=len(items),
    )


# ===== 7.10 Revoke Invite =====

@participation_router.delete('/{event_id}/invites/{invite_id}', status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invite(
    event_id: int,
    invite_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke an invite."""
    event = get_event_or_404(db, event_id)

    invite = db.query(EventInvite).filter(
        EventInvite.id == invite_id,
        EventInvite.event_id == event_id
    ).first()

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Invite not found'
        )

    # Organizer or invite creator can revoke
    is_organizer = event_crud.is_organizer(db, current_user.id, event_id)
    is_creator = invite.created_by == current_user.id

    if not is_organizer and not is_creator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer or invite creator can revoke'
        )

    db.delete(invite)
    db.commit()
    return None
