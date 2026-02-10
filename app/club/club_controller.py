from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth.auth_service import get_current_user, get_current_user_optional
from ..user.user_model import User
from ..enums.privacy import Privacy
from ..enums.club_role import ClubRole
from ..enums.membership_status import MembershipStatus
from . import club_crud
from .club_schema import (
    ClubCreate,
    ClubUpdate,
    ClubResponse,
    ClubDetailResponse,
    ClubListItem,
    ClubListResponse,
    ClubOwnerBrief,
    ClubLogoResponse,
    ClubMemberItem,
    ClubMembersResponse,
    MemberUserBrief,
)

club_router = APIRouter(prefix='/api/clubs', tags=['clubs'])


@club_router.post('', response_model=ClubResponse, status_code=status.HTTP_201_CREATED)
async def create_club(
    data: ClubCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new club. Creator becomes owner."""
    # Check name uniqueness
    existing = club_crud.get_club_by_name(db, data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Club with this name already exists'
        )

    club = club_crud.create_club(db, data, current_user.id)
    members_count = club_crud.get_members_count(db, club.id)

    return ClubResponse(
        id=club.id,
        name=club.name,
        description=club.description,
        logo=club.logo,
        location=club.location,
        privacy=club.privacy,
        owner_id=club.owner_id,
        members_count=members_count,
        created_at=club.created_at,
    )


@club_router.get('/{club_id}', response_model=ClubDetailResponse)
async def get_club(
    club_id: int,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Get club details."""
    club = club_crud.get_club_by_id(db, club_id)
    if not club:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Club not found'
        )

    # Check visibility for private clubs
    if club.privacy == Privacy.PRIVATE:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Club not found'
            )
        membership = club_crud.get_membership(db, current_user.id, club_id)
        if not membership or membership.status != MembershipStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Club not found'
            )

    members_count = club_crud.get_members_count(db, club.id)

    # Get membership info if authenticated
    membership_status = None
    membership_role = None
    if current_user:
        membership_status = club_crud.get_membership_status(db, current_user.id, club_id)
        if membership_status == MembershipStatus.ACTIVE:
            membership_role = club_crud.get_membership_role(db, current_user.id, club_id)

    return ClubDetailResponse(
        id=club.id,
        name=club.name,
        description=club.description,
        logo=club.logo,
        location=club.location,
        privacy=club.privacy,
        owner=ClubOwnerBrief(
            id=club.owner.id,
            username_display=club.owner.username_display,
            first_name=club.owner.first_name,
        ),
        members_count=members_count,
        membership_status=membership_status,
        membership_role=membership_role,
        created_at=club.created_at,
    )


@club_router.get('', response_model=ClubListResponse)
async def list_clubs(
    q: str | None = Query(None, description='Search query'),
    privacy: Privacy | None = Query(None, description='Filter by privacy'),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """List and search clubs."""
    current_user_id = current_user.id if current_user else None
    clubs, total = club_crud.search_clubs(
        db, query=q, privacy=privacy, current_user_id=current_user_id,
        limit=limit, offset=offset
    )

    club_items = []
    for club in clubs:
        members_count = club_crud.get_members_count(db, club.id)
        membership_status = None
        if current_user:
            membership_status = club_crud.get_membership_status(db, current_user.id, club.id)

        club_items.append(ClubListItem(
            id=club.id,
            name=club.name,
            logo=club.logo,
            location=club.location,
            privacy=club.privacy,
            members_count=members_count,
            membership_status=membership_status,
        ))

    return ClubListResponse(
        clubs=club_items,
        total=total,
        limit=limit,
        offset=offset,
    )


@club_router.patch('/{club_id}', response_model=ClubDetailResponse)
async def update_club(
    club_id: int,
    data: ClubUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update club. Only owner or coach can update."""
    club = club_crud.get_club_by_id(db, club_id)
    if not club:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Club not found'
        )

    # Check permissions
    if not club_crud.is_club_admin(db, current_user.id, club_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only owner or coach can update the club'
        )

    # Check name uniqueness if changing name
    if data.name and data.name != club.name:
        existing = club_crud.get_club_by_name(db, data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Club with this name already exists'
            )

    updated_club = club_crud.update_club(db, club, data)
    members_count = club_crud.get_members_count(db, club.id)
    membership_status = club_crud.get_membership_status(db, current_user.id, club_id)
    membership_role = club_crud.get_membership_role(db, current_user.id, club_id)

    return ClubDetailResponse(
        id=updated_club.id,
        name=updated_club.name,
        description=updated_club.description,
        logo=updated_club.logo,
        location=updated_club.location,
        privacy=updated_club.privacy,
        owner=ClubOwnerBrief(
            id=updated_club.owner.id,
            username_display=updated_club.owner.username_display,
            first_name=updated_club.owner.first_name,
        ),
        members_count=members_count,
        membership_status=membership_status,
        membership_role=membership_role,
        created_at=updated_club.created_at,
    )


@club_router.post('/{club_id}/logo', response_model=ClubLogoResponse)
async def upload_club_logo(
    club_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload club logo. Only owner or coach can upload."""
    club = club_crud.get_club_by_id(db, club_id)
    if not club:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Club not found'
        )

    # Check permissions
    if not club_crud.is_club_admin(db, current_user.id, club_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only owner or coach can upload logo'
        )

    # TODO: Implement file upload to MinIO
    # For now, return a placeholder
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail='Logo upload not yet implemented'
    )


@club_router.get('/{club_id}/members', response_model=ClubMembersResponse)
async def get_club_members(
    club_id: int,
    role: ClubRole | None = Query(None, description='Filter by role'),
    member_status: MembershipStatus | None = Query(None, alias='status', description='Filter by status'),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """List club members."""
    club = club_crud.get_club_by_id(db, club_id)
    if not club:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Club not found'
        )

    # Check visibility for private clubs
    if club.privacy == Privacy.PRIVATE:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Club not found'
            )
        membership = club_crud.get_membership(db, current_user.id, club_id)
        if not membership or membership.status != MembershipStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Club not found'
            )

    # Determine if user can see pending members
    can_see_pending = False
    if current_user:
        can_see_pending = club_crud.is_club_admin(db, current_user.id, club_id)

    # If status filter is pending but user can't see pending, deny
    if member_status == MembershipStatus.PENDING and not can_see_pending:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only club admins can view pending members'
        )

    members, total = club_crud.get_club_members(
        db, club_id, role=role, status=member_status,
        can_see_pending=can_see_pending, limit=limit, offset=offset
    )

    member_items = []
    for membership in members:
        user = membership.user
        member_items.append(ClubMemberItem(
            id=membership.id,
            user=MemberUserBrief(
                id=user.id,
                username_display=user.username_display,
                first_name=user.first_name,
                last_name=f"{user.last_name[0]}." if user.last_name else None,
                logo=user.logo,
            ),
            role=membership.role,
            status=membership.status,
            joined_at=membership.joined_at,
        ))

    return ClubMembersResponse(
        members=member_items,
        total=total,
        limit=limit,
        offset=offset,
    )


@club_router.delete('/{club_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_club(
    club_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete club. Only owner can delete."""
    club = club_crud.get_club_by_id(db, club_id)
    if not club:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Club not found'
        )

    # Only owner can delete
    if not club_crud.is_club_owner(db, current_user.id, club_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only club owner can delete the club'
        )

    # TODO: Notify all active members about deletion

    club_crud.delete_club(db, club)
    return None
