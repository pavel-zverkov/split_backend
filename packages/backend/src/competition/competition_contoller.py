from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth.auth_service import get_current_user, get_current_user_optional
from ..user.user_model import User
from ..enums.competition_status import CompetitionStatus
from ..enums.event_role import EventRole
from ..event import event_crud
from . import competition_crud
from .competition_schema import (
    CompetitionCreate,
    CompetitionUpdate,
    CompetitionResponse,
    CompetitionListItem,
    CompetitionListResponse,
    CompetitionDetailResponse,
    EventBrief,
    CompetitionTeamItem,
    CompetitionTeamListResponse,
    TeamUserBrief,
    AssignTeamMemberRequest,
    CompetitionTeamResponse,
)

competition_router = APIRouter(tags=['competitions'])


# ===== Helper Functions =====

def get_event_or_404(db: Session, event_id: int):
    event = event_crud.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Event not found'
        )
    return event


def get_competition_or_404(db: Session, competition_id: int, event_id: int | None = None):
    competition = competition_crud.get_competition(db, competition_id)
    if not competition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Competition not found'
        )
    if event_id and competition.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Competition not found in this event'
        )
    return competition


# ===== 8.1 Create Competition =====

@competition_router.post(
    '/api/events/{event_id}/competitions',
    response_model=CompetitionResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_competition(
    event_id: int,
    data: CompetitionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new competition in an event."""
    event = get_event_or_404(db, event_id)

    # Check permissions
    if not competition_crud.can_manage_competition(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only chief organizer, secretary, or judge can create competitions'
        )

    competition = competition_crud.create_competition(
        db, event_id, data, sport_kind=event.sport_kind
    )

    return CompetitionResponse(
        id=competition.id,
        event_id=competition.event_id,
        name=competition.name,
        description=competition.description,
        date=competition.date,
        sport_kind=competition.sport_kind,
        start_format=competition.start_format,
        class_list=competition.class_list,
        control_points_list=competition.control_points_list,
        distance_meters=competition.distance_meters,
        location=competition.location,
        status=competition.status,
        registrations_count=0,
        created_at=competition.created_at,
    )


# ===== 8.2 List Competitions =====

@competition_router.get(
    '/api/events/{event_id}/competitions',
    response_model=CompetitionListResponse
)
async def list_competitions(
    event_id: int,
    competition_status: CompetitionStatus | None = Query(None, alias='status'),
    competition_date: date | None = Query(None, alias='date'),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List competitions in an event."""
    event = get_event_or_404(db, event_id)

    competitions, total = competition_crud.get_competitions_by_event(
        db, event_id,
        status=competition_status,
        competition_date=competition_date,
        limit=limit,
        offset=offset
    )

    items = []
    for comp in competitions:
        items.append(CompetitionListItem(
            id=comp.id,
            name=comp.name,
            date=comp.date,
            sport_kind=comp.sport_kind,
            start_format=comp.start_format,
            distance_meters=comp.distance_meters,
            location=comp.location,
            status=comp.status,
            registrations_count=competition_crud.get_registrations_count(db, comp.id),
            classes_count=len(comp.class_list) if comp.class_list else 0,
        ))

    return CompetitionListResponse(
        competitions=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# ===== 8.3 Get Competition Details =====

@competition_router.get(
    '/api/events/{event_id}/competitions/{competition_id}',
    response_model=CompetitionDetailResponse
)
async def get_competition(
    event_id: int,
    competition_id: int,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Get competition details."""
    event = get_event_or_404(db, event_id)
    competition = get_competition_or_404(db, competition_id, event_id)

    team, team_count = competition_crud.get_competition_team(db, competition_id, limit=1000)

    return CompetitionDetailResponse(
        id=competition.id,
        event_id=competition.event_id,
        event=EventBrief(id=event.id, name=event.name),
        name=competition.name,
        description=competition.description,
        date=competition.date,
        sport_kind=competition.sport_kind,
        start_format=competition.start_format,
        class_list=competition.class_list,
        control_points_list=competition.control_points_list,
        distance_meters=competition.distance_meters,
        location=competition.location,
        status=competition.status,
        registrations_count=competition_crud.get_registrations_count(db, competition_id),
        team_count=team_count,
        my_registration=None,  # TODO: Implement when registration is done
        created_at=competition.created_at,
    )


# ===== 8.4 Update Competition =====

@competition_router.patch(
    '/api/events/{event_id}/competitions/{competition_id}',
    response_model=CompetitionResponse
)
async def update_competition(
    event_id: int,
    competition_id: int,
    data: CompetitionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a competition."""
    event = get_event_or_404(db, event_id)
    competition = get_competition_or_404(db, competition_id, event_id)

    # Check permissions
    if not competition_crud.can_manage_competition(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only chief organizer, secretary, or judge can update competitions'
        )

    # Validate status transition
    if data.status and not competition_crud.is_valid_status_transition(competition.status, data.status):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid status transition from {competition.status.value} to {data.status.value}'
        )

    # Check if modifying class_list/control_points_list with existing results
    if (data.class_list or data.control_points_list) and competition_crud.get_results_count(db, competition_id) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Cannot modify class_list or control_points_list when results exist'
        )

    updated = competition_crud.update_competition(db, competition, data)

    return CompetitionResponse(
        id=updated.id,
        event_id=updated.event_id,
        name=updated.name,
        description=updated.description,
        date=updated.date,
        sport_kind=updated.sport_kind,
        start_format=updated.start_format,
        class_list=updated.class_list,
        control_points_list=updated.control_points_list,
        distance_meters=updated.distance_meters,
        location=updated.location,
        status=updated.status,
        registrations_count=competition_crud.get_registrations_count(db, competition_id),
        created_at=updated.created_at,
    )


# ===== 8.5 Delete Competition =====

@competition_router.delete(
    '/api/events/{event_id}/competitions/{competition_id}',
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_competition(
    event_id: int,
    competition_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a competition."""
    event = get_event_or_404(db, event_id)
    competition = get_competition_or_404(db, competition_id, event_id)

    # Check permissions
    if not competition_crud.can_delete_competition(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only chief organizer or secretary can delete competitions'
        )

    # Cannot delete if in progress
    if competition.status == CompetitionStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Cannot delete competition in progress'
        )

    competition_crud.delete_competition(db, competition)
    return None


# ===== 8.6 List Competition Team =====

@competition_router.get(
    '/api/competitions/{competition_id}/team',
    response_model=CompetitionTeamListResponse
)
async def list_competition_team(
    competition_id: int,
    role: EventRole | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List competition team members."""
    competition = get_competition_or_404(db, competition_id)

    team, total = competition_crud.get_competition_team(
        db, competition_id, role=role, limit=limit, offset=offset
    )

    items = []
    for member in team:
        items.append(CompetitionTeamItem(
            user=TeamUserBrief(
                id=member['user'].id,
                username_display=member['user'].username_display,
                first_name=member['user'].first_name,
                last_name=f"{member['user'].last_name[0]}." if member['user'].last_name else None,
            ),
            role=member['role'],
            position=member['position'],
            inherited=member['inherited'],
        ))

    return CompetitionTeamListResponse(
        team=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# ===== 8.7 Assign Team Member =====

@competition_router.post(
    '/api/competitions/{competition_id}/team',
    response_model=CompetitionTeamResponse,
    status_code=status.HTTP_201_CREATED
)
async def assign_team_member(
    competition_id: int,
    data: AssignTeamMemberRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Assign a team member to a competition."""
    competition = get_competition_or_404(db, competition_id)

    # Check permissions
    if not competition_crud.can_delete_competition(db, current_user.id, competition.event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only chief organizer or secretary can assign team members'
        )

    # Check user is event team member
    if not competition_crud.is_event_team_member(db, data.user_id, competition.event_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='User is not an event team member'
        )

    assignment = competition_crud.assign_team_member(db, competition_id, data.user_id, data.role)

    return CompetitionTeamResponse(
        user_id=assignment.user_id,
        competition_id=assignment.competition_id,
        role=assignment.role,
        position=None,
        inherited=False,
    )


# ===== 8.8 Remove from Competition Team =====

@competition_router.delete(
    '/api/competitions/{competition_id}/team/{user_id}',
    status_code=status.HTTP_204_NO_CONTENT
)
async def remove_from_competition_team(
    competition_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a team member from a competition."""
    competition = get_competition_or_404(db, competition_id)

    # Check permissions
    if not competition_crud.can_delete_competition(db, current_user.id, competition.event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only chief organizer or secretary can remove team members'
        )

    competition_crud.remove_from_competition_team(db, competition_id, user_id)
    return None
