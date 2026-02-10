from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth.auth_service import get_current_user
from ..user.user_model import User
from ..enums.privacy import Privacy
from ..enums.club_role import ClubRole
from ..enums.membership_status import MembershipStatus
from . import club_crud
from .club_schema import (
    MembershipResponse,
    MembershipStatusUpdate,
    MembershipRoleUpdate,
    TransferOwnershipRequest,
    TransferOwnershipResponse,
    AddMemberRequest,
)
from ..user import user_crud

club_membership_router = APIRouter(prefix='/api/clubs', tags=['club-membership'])


@club_membership_router.post('/{club_id}/join', response_model=MembershipResponse, status_code=status.HTTP_201_CREATED)
async def join_club(
    club_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Join a club. Status depends on club's privacy settings."""
    club = club_crud.get_club_by_id(db, club_id)
    if not club:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Club not found'
        )

    # Check if private club - can't join private clubs directly
    if club.privacy == Privacy.PRIVATE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Cannot join private club'
        )

    # Check if already a member
    existing = club_crud.get_membership(db, current_user.id, club_id)
    if existing:
        if existing.status == MembershipStatus.REJECTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Membership request was rejected'
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Already a member or request pending'
        )

    # Determine initial status based on privacy
    initial_status = club_crud.get_initial_membership_status(club)

    membership = club_crud.create_membership(db, current_user.id, club_id, initial_status)

    return MembershipResponse(
        id=membership.id,
        user_id=membership.user_id,
        club_id=membership.club_id,
        role=membership.role,
        status=membership.status,
        joined_at=membership.joined_at,
        created_at=membership.created_at,
    )


@club_membership_router.post('/{club_id}/members', response_model=MembershipResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    club_id: int,
    data: AddMemberRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a member to the club. Only owner or coach can do this. Useful for adding ghost users."""
    club = club_crud.get_club_by_id(db, club_id)
    if not club:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Club not found'
        )

    # Check permissions - must be admin
    if not club_crud.is_club_admin(db, current_user.id, club_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only owner or coach can add members'
        )

    # Verify user exists
    target_user = user_crud.get_user_by_id(db, data.user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found'
        )

    # Check if already a member
    existing = club_crud.get_membership(db, data.user_id, club_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='User is already a member or has pending request'
        )

    # Cannot set owner role
    if data.role == ClubRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Cannot set owner role. Use transfer ownership endpoint.'
        )

    # Create membership with active status (admin-added members are immediately active)
    membership = club_crud.create_membership(
        db, data.user_id, club_id,
        status=MembershipStatus.ACTIVE,
        role=data.role
    )

    return MembershipResponse(
        id=membership.id,
        user_id=membership.user_id,
        club_id=membership.club_id,
        role=membership.role,
        status=membership.status,
        joined_at=membership.joined_at,
        created_at=membership.created_at,
    )


@club_membership_router.patch('/{club_id}/members/{membership_id}', status_code=status.HTTP_200_OK)
async def update_membership_request(
    club_id: int,
    membership_id: int,
    update: MembershipStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Approve or reject a membership request. Only owner or coach can do this."""
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
            detail='Only owner or coach can approve/reject membership requests'
        )

    membership = club_crud.get_membership_by_id(db, membership_id)
    if not membership or membership.club_id != club_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Membership request not found'
        )

    # Can only update pending requests
    if membership.status != MembershipStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Can only update pending membership requests'
        )

    # Validate status
    if update.status not in [MembershipStatus.ACTIVE, MembershipStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Status must be active or rejected'
        )

    club_crud.update_membership_status(db, membership, update.status)

    return {'status': 'ok'}


@club_membership_router.delete('/{club_id}/members/me', status_code=status.HTTP_204_NO_CONTENT)
async def leave_club(
    club_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Leave a club. Owner cannot leave - must transfer ownership first."""
    club = club_crud.get_club_by_id(db, club_id)
    if not club:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Club not found'
        )

    membership = club_crud.get_membership(db, current_user.id, club_id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Not a member of this club'
        )

    # Owner cannot leave
    if membership.role == ClubRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Owner cannot leave club. Transfer ownership first.'
        )

    club_crud.delete_membership(db, membership)
    return None


@club_membership_router.delete('/{club_id}/members/{user_id}', status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    club_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a member from club. Owner can remove coach/member, coach can remove member."""
    club = club_crud.get_club_by_id(db, club_id)
    if not club:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Club not found'
        )

    # Get actor's membership
    actor_membership = club_crud.get_membership(db, current_user.id, club_id)
    if not actor_membership or actor_membership.status != MembershipStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Not a member of this club'
        )

    # Check if actor is admin
    if actor_membership.role not in [ClubRole.OWNER, ClubRole.COACH]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only owner or coach can remove members'
        )

    # Get target's membership
    target_membership = club_crud.get_membership(db, user_id, club_id)
    if not target_membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User is not a member of this club'
        )

    # Cannot remove yourself via this endpoint
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Use leave endpoint to leave club'
        )

    # Check permission matrix
    if not club_crud.can_remove_member(actor_membership.role, target_membership.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Insufficient permissions to remove this member'
        )

    club_crud.delete_membership(db, target_membership)
    return None


@club_membership_router.patch('/{club_id}/members/{user_id}/role', response_model=MembershipResponse)
async def update_member_role(
    club_id: int,
    user_id: int,
    update: MembershipRoleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Assign or change member role. Only owner can do this."""
    club = club_crud.get_club_by_id(db, club_id)
    if not club:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Club not found'
        )

    # Only owner can change roles
    if not club_crud.is_club_owner(db, current_user.id, club_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only owner can change member roles'
        )

    # Cannot set owner role - use transfer ownership
    if update.role == ClubRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Cannot set owner role. Use transfer ownership endpoint.'
        )

    # Get target's membership
    target_membership = club_crud.get_membership(db, user_id, club_id)
    if not target_membership or target_membership.status != MembershipStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User is not an active member of this club'
        )

    # Cannot change own role
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Cannot change your own role'
        )

    # Cannot change owner's role
    if target_membership.role == ClubRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Cannot change owner role. Use transfer ownership endpoint.'
        )

    updated = club_crud.update_membership_role(db, target_membership, update.role)

    return MembershipResponse(
        id=updated.id,
        user_id=updated.user_id,
        club_id=updated.club_id,
        role=updated.role,
        status=updated.status,
        joined_at=updated.joined_at,
        created_at=updated.created_at,
    )


@club_membership_router.post('/{club_id}/transfer-ownership', response_model=TransferOwnershipResponse)
async def transfer_ownership(
    club_id: int,
    request: TransferOwnershipRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Transfer club ownership to another active member."""
    club = club_crud.get_club_by_id(db, club_id)
    if not club:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Club not found'
        )

    # Only owner can transfer
    if not club_crud.is_club_owner(db, current_user.id, club_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only owner can transfer ownership'
        )

    # Cannot transfer to self
    if request.new_owner_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Cannot transfer ownership to yourself'
        )

    # Get new owner's membership
    new_owner_membership = club_crud.get_membership(db, request.new_owner_id, club_id)
    if not new_owner_membership or new_owner_membership.status != MembershipStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='New owner must be an active club member'
        )

    # Get old owner's membership
    old_owner_membership = club_crud.get_membership(db, current_user.id, club_id)

    updated_club = club_crud.transfer_ownership(db, club, old_owner_membership, new_owner_membership)

    return TransferOwnershipResponse(
        id=updated_club.id,
        name=updated_club.name,
        owner_id=updated_club.owner_id,
        message='Ownership transferred successfully'
    )
