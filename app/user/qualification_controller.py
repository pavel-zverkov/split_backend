from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth.auth_service import get_current_user, get_current_user_optional
from ..enums.privacy import Privacy
from .user_model import User
from . import user_crud
from . import follow_crud
from . import qualification_crud
from .qualification_schema import (
    QualificationCreate,
    QualificationUpdate,
    QualificationResponse,
    QualificationPublicResponse,
    QualificationsListResponse,
    QualificationsPublicListResponse,
)

qualification_router = APIRouter(prefix='/api/users', tags=['qualifications'])


def can_view_qualifications(
    db: Session,
    viewer: User | None,
    target_user: User
) -> bool:
    """Check if viewer can see target user's qualifications based on privacy."""
    # Self can always see
    if viewer and viewer.id == target_user.id:
        return True

    if target_user.privacy_default == Privacy.PUBLIC:
        return True

    if target_user.privacy_default == Privacy.FOLLOWERS:
        if viewer:
            return follow_crud.is_following(db, viewer.id, target_user.id)
        return False

    # Privacy.PRIVATE - only self can see
    return False


@qualification_router.post('/me/qualifications', response_model=QualificationResponse, status_code=status.HTTP_201_CREATED)
async def add_qualification(
    data: QualificationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a qualification to current user's profile."""
    # Check for duplicate
    existing = qualification_crud.get_duplicate_qualification(
        db, current_user.id, data.type, data.sport_kind, data.rank
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Qualification with same type, sport kind, and rank already exists'
        )

    qualification = qualification_crud.create_qualification(db, current_user.id, data)

    return QualificationResponse(
        id=qualification.id,
        type=qualification.type,
        sport_kind=qualification.sport_kind,
        rank=qualification.rank,
        issued_date=qualification.issued_date,
        valid_until=qualification.valid_until,
        document_number=qualification.document_number,
        confirmed=qualification.confirmed,
        created_at=qualification.created_at,
    )


@qualification_router.get('/me/qualifications', response_model=QualificationsListResponse)
async def get_my_qualifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's qualifications."""
    qualifications = qualification_crud.get_user_qualifications(db, current_user.id)

    return QualificationsListResponse(
        qualifications=[
            QualificationResponse(
                id=q.id,
                type=q.type,
                sport_kind=q.sport_kind,
                rank=q.rank,
                issued_date=q.issued_date,
                valid_until=q.valid_until,
                document_number=q.document_number,
                confirmed=q.confirmed,
                created_at=q.created_at,
            )
            for q in qualifications
        ]
    )


@qualification_router.get('/{user_id}/qualifications', response_model=QualificationsPublicListResponse)
async def get_user_qualifications(
    user_id: int,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Get a user's qualifications. Visibility depends on user's privacy settings."""
    target_user = user_crud.get_user_by_id(db, user_id)
    if not target_user or not target_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found'
        )

    # Check if viewer can see qualifications
    if not can_view_qualifications(db, current_user, target_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='You do not have permission to view this user\'s qualifications'
        )

    qualifications = qualification_crud.get_user_qualifications(db, user_id)

    return QualificationsPublicListResponse(
        qualifications=[
            QualificationPublicResponse(
                id=q.id,
                type=q.type,
                sport_kind=q.sport_kind,
                rank=q.rank,
                issued_date=q.issued_date,
                valid_until=q.valid_until,
                confirmed=q.confirmed,
            )
            for q in qualifications
        ]
    )


@qualification_router.patch('/me/qualifications/{qualification_id}', response_model=QualificationResponse)
async def update_qualification(
    qualification_id: int,
    data: QualificationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a qualification."""
    qualification = qualification_crud.get_qualification_by_id(db, qualification_id)
    if not qualification or qualification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Qualification not found'
        )

    # Check for duplicate if rank is being changed
    if data.rank and data.rank != qualification.rank:
        existing = qualification_crud.get_duplicate_qualification(
            db, current_user.id, qualification.type, qualification.sport_kind,
            data.rank, exclude_id=qualification_id
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Qualification with same type, sport kind, and rank already exists'
            )

    updated = qualification_crud.update_qualification(db, qualification, data)

    return QualificationResponse(
        id=updated.id,
        type=updated.type,
        sport_kind=updated.sport_kind,
        rank=updated.rank,
        issued_date=updated.issued_date,
        valid_until=updated.valid_until,
        document_number=updated.document_number,
        confirmed=updated.confirmed,
        created_at=updated.created_at,
    )


@qualification_router.delete('/me/qualifications/{qualification_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_qualification(
    qualification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a qualification."""
    qualification = qualification_crud.get_qualification_by_id(db, qualification_id)
    if not qualification or qualification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Qualification not found'
        )

    qualification_crud.delete_qualification(db, qualification)
    return None
