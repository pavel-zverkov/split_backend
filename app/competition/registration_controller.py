from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth.auth_service import get_current_user, get_current_user_optional
from ..user.user_model import User
from ..enums.registration_status import RegistrationStatus
from . import competition_crud, registration_crud
from .registration_schema import (
    RegisterRequest,
    RegistrationResponse,
    RegistrationItem,
    RegistrationUserBrief,
    RegistrationsListResponse,
    UpdateRegistrationRequest,
    BatchUpdateRequest,
    BatchUpdateResponse,
    BatchUpdateResultItem,
    StartListResponse,
    StartListItem,
    StartListUserBrief,
    ClubBrief,
    ClassSummary,
    CompetitionBrief,
    AddRegistrationRequest,
)
from ..user import user_crud
from ..club import club_crud

registration_router = APIRouter(prefix='/api/competitions', tags=['competition-registration'])


# ===== Helper Functions =====

def get_competition_or_404(db: Session, competition_id: int):
    competition = competition_crud.get_competition(db, competition_id)
    if not competition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Competition not found'
        )
    return competition


# ===== 9.1 Register for Competition =====

@registration_router.post('/{competition_id}/register', response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_for_competition(
    competition_id: int,
    data: RegisterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Register for a competition."""
    competition = get_competition_or_404(db, competition_id)

    # Check if user has approved event participation
    if not registration_crud.has_approved_event_participation(db, current_user.id, competition.event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='You must have approved event participation to register'
        )

    # Check if registration is allowed
    if not registration_crud.can_register(db, competition):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Registration is closed for this competition'
        )

    # Check if already registered
    existing = registration_crud.get_registration_by_user(db, current_user.id, competition_id)
    if existing:
        if existing.status != RegistrationStatus.REJECTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Already registered for this competition'
            )
        # Delete rejected registration to allow re-registration
        registration_crud.delete_registration(db, existing)

    # Validate class
    if competition.class_list and data.competition_class not in competition.class_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid class. Available: {", ".join(competition.class_list)}'
        )

    registration = registration_crud.create_registration(
        db, current_user.id, competition_id, data.competition_class
    )

    return RegistrationResponse(
        id=registration.id,
        user_id=registration.user_id,
        competition_id=registration.competition_id,
        competition_class=registration.class_,
        bib_number=registration.bib_number,
        start_time=registration.start_time,
        status=registration.status,
        created_at=registration.created_at,
    )


# ===== 9.1b Add Registration (by organizer) =====

@registration_router.post('/{competition_id}/registrations', response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
async def add_registration(
    competition_id: int,
    data: AddRegistrationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a registration for a user. Only organizer/secretary can do this. Useful for adding ghost users."""
    competition = get_competition_or_404(db, competition_id)

    # Check permissions
    if not registration_crud.can_manage_registrations(db, current_user.id, competition.event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer or secretary can add registrations'
        )

    # Verify user exists
    target_user = user_crud.get_user_by_id(db, data.user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found'
        )

    # Check if already registered
    existing = registration_crud.get_registration_by_user(db, data.user_id, competition_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='User is already registered for this competition'
        )

    # Validate class
    if competition.class_list and data.competition_class not in competition.class_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid class. Available: {", ".join(competition.class_list)}'
        )

    # Validate bib number uniqueness
    if data.bib_number and not registration_crud.is_bib_number_unique(
        db, competition_id, data.bib_number
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Bib number already assigned'
        )

    # Create registration with registered status (organizer can confirm later)
    registration = registration_crud.create_registration(
        db, data.user_id, competition_id, data.competition_class,
        bib_number=data.bib_number,
        start_time=data.start_time,
        status=RegistrationStatus.REGISTERED
    )

    return RegistrationResponse(
        id=registration.id,
        user_id=registration.user_id,
        competition_id=registration.competition_id,
        competition_class=registration.class_,
        bib_number=registration.bib_number,
        start_time=registration.start_time,
        status=registration.status,
        created_at=registration.created_at,
    )


# ===== 9.2 Get My Registration =====

@registration_router.get('/{competition_id}/registrations/me', response_model=RegistrationResponse)
async def get_my_registration(
    competition_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's registration for a competition."""
    competition = get_competition_or_404(db, competition_id)

    registration = registration_crud.get_registration_by_user(db, current_user.id, competition_id)
    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Not registered for this competition'
        )

    return RegistrationResponse(
        id=registration.id,
        user_id=registration.user_id,
        competition_id=registration.competition_id,
        competition_class=registration.class_,
        bib_number=registration.bib_number,
        start_time=registration.start_time,
        status=registration.status,
        created_at=registration.created_at,
    )


# ===== 9.3 List Registrations =====

@registration_router.get('/{competition_id}/registrations', response_model=RegistrationsListResponse)
async def list_registrations(
    competition_id: int,
    competition_class: str | None = Query(None, alias='class'),
    registration_status: RegistrationStatus | None = Query(None, alias='status'),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """List competition registrations."""
    competition = get_competition_or_404(db, competition_id)

    # Check if user can see all statuses
    can_see_all = current_user and registration_crud.can_manage_registrations(
        db, current_user.id, competition.event_id
    )

    # Non-managers can only see confirmed
    if not can_see_all:
        if registration_status and registration_status != RegistrationStatus.CONFIRMED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Only confirmed registrations are visible'
            )
        registration_status = RegistrationStatus.CONFIRMED

    registrations, total = registration_crud.get_registrations(
        db, competition_id,
        competition_class=competition_class,
        status=registration_status,
        limit=limit,
        offset=offset
    )

    items = []
    for reg in registrations:
        items.append(RegistrationItem(
            id=reg.id,
            user=RegistrationUserBrief(
                id=reg.user.id,
                username_display=reg.user.username_display,
                first_name=reg.user.first_name,
                last_name=f"{reg.user.last_name[0]}." if reg.user.last_name else None,
                logo=reg.user.logo,
            ),
            competition_class=reg.class_,
            bib_number=reg.bib_number,
            start_time=reg.start_time,
            status=reg.status,
        ))

    return RegistrationsListResponse(
        registrations=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# ===== 9.4 Get Start List =====

@registration_router.get('/{competition_id}/start-list', response_model=StartListResponse)
async def get_start_list(
    competition_id: int,
    competition_class: str | None = Query(None, alias='class'),
    db: Session = Depends(get_db)
):
    """Get competition start list."""
    competition = get_competition_or_404(db, competition_id)

    registrations = registration_crud.get_start_list(db, competition_id, competition_class)
    class_summaries = registration_crud.get_class_summaries(db, competition_id)

    items = []
    for reg in registrations:
        # Get user's club
        user_club = club_crud.get_user_active_club(db, reg.user.id)
        club_brief = None
        if user_club:
            club_brief = ClubBrief(id=user_club.id, name=user_club.name)

        items.append(StartListItem(
            bib_number=reg.bib_number,
            start_time=reg.start_time,
            competition_class=reg.class_,
            user=StartListUserBrief(
                id=reg.user.id,
                username_display=reg.user.username_display,
                first_name=reg.user.first_name,
                last_name=f"{reg.user.last_name[0]}." if reg.user.last_name else None,
                club=club_brief,
            ),
        ))

    return StartListResponse(
        competition=CompetitionBrief(
            id=competition.id,
            name=competition.name,
            date=str(competition.date),
        ),
        start_list=items,
        classes=[
            ClassSummary(
                competition_class=s['class'] or '',
                count=s['count'],
                first_start=s['first_start'],
            )
            for s in class_summaries
        ],
        total=len(items),
    )


# ===== 9.5 Update Registration =====

@registration_router.patch('/{competition_id}/registrations/{registration_id}', response_model=RegistrationResponse)
async def update_registration(
    competition_id: int,
    registration_id: int,
    data: UpdateRegistrationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a registration (organizer/secretary only)."""
    competition = get_competition_or_404(db, competition_id)

    # Check permissions
    if not registration_crud.can_manage_registrations(db, current_user.id, competition.event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer or secretary can update registrations'
        )

    registration = registration_crud.get_registration(db, registration_id)
    if not registration or registration.competition_id != competition_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Registration not found'
        )

    # Validate bib number uniqueness
    if data.bib_number and not registration_crud.is_bib_number_unique(
        db, competition_id, data.bib_number, registration_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Bib number already assigned'
        )

    # Validate class
    if data.competition_class and competition.class_list:
        if data.competition_class not in competition.class_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Invalid class. Available: {", ".join(competition.class_list)}'
            )

    updated = registration_crud.update_registration(
        db, registration,
        bib_number=data.bib_number,
        start_time=data.start_time,
        status=data.status,
        competition_class=data.competition_class,
    )

    return RegistrationResponse(
        id=updated.id,
        user_id=updated.user_id,
        competition_id=updated.competition_id,
        competition_class=updated.class_,
        bib_number=updated.bib_number,
        start_time=updated.start_time,
        status=updated.status,
        created_at=updated.created_at,
    )


# ===== 9.6 Batch Assign =====

@registration_router.post('/{competition_id}/registrations/batch', response_model=BatchUpdateResponse)
async def batch_update_registrations(
    competition_id: int,
    data: BatchUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Batch assign bibs and start times."""
    competition = get_competition_or_404(db, competition_id)

    # Check permissions
    if not registration_crud.can_manage_registrations(db, current_user.id, competition.event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer or secretary can update registrations'
        )

    # Check for duplicate bib numbers in batch
    bib_numbers = [r.bib_number for r in data.registrations if r.bib_number]
    if len(bib_numbers) != len(set(bib_numbers)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Duplicate bib numbers in batch'
        )

    results = []
    for item in data.registrations:
        registration = registration_crud.get_registration(db, item.registration_id)
        if not registration or registration.competition_id != competition_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Invalid registration_id: {item.registration_id}'
            )

        # Check bib uniqueness
        if item.bib_number and not registration_crud.is_bib_number_unique(
            db, competition_id, item.bib_number, item.registration_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Bib number {item.bib_number} already assigned'
            )

        updated = registration_crud.update_registration(
            db, registration,
            bib_number=item.bib_number,
            start_time=item.start_time,
            status=data.set_status,
        )

        results.append(BatchUpdateResultItem(
            registration_id=updated.id,
            bib_number=updated.bib_number,
            status=updated.status,
        ))

    return BatchUpdateResponse(
        updated=len(results),
        registrations=results,
    )


# ===== 9.7 Cancel My Registration =====

@registration_router.delete('/{competition_id}/registrations/me', status_code=status.HTTP_204_NO_CONTENT)
async def cancel_my_registration(
    competition_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel own registration."""
    competition = get_competition_or_404(db, competition_id)

    registration = registration_crud.get_registration_by_user(db, current_user.id, competition_id)
    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Not registered for this competition'
        )

    # Check if has result
    if registration_crud.has_result(db, registration.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Cannot cancel: result exists'
        )

    # Check if can cancel
    if not registration_crud.can_cancel_registration(db, competition):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Cannot cancel: competition in progress'
        )

    registration_crud.delete_registration(db, registration)
    return None


# ===== 9.8 Remove Participant Registration =====

@registration_router.delete('/{competition_id}/registrations/{registration_id}', status_code=status.HTTP_204_NO_CONTENT)
async def remove_registration(
    competition_id: int,
    registration_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a participant's registration (organizer/secretary only)."""
    competition = get_competition_or_404(db, competition_id)

    # Check permissions
    if not registration_crud.can_manage_registrations(db, current_user.id, competition.event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer or secretary can remove registrations'
        )

    registration = registration_crud.get_registration(db, registration_id)
    if not registration or registration.competition_id != competition_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Registration not found'
        )

    # Check if has result
    if registration_crud.has_result(db, registration.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Cannot delete: result exists'
        )

    registration_crud.delete_registration(db, registration)
    return None
