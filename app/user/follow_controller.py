from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth.auth_service import get_current_user, get_current_user_optional
from ..enums.follow_status import FollowStatus
from .user_model import User
from .user_follow_model import UserFollow
from . import user_crud
from . import follow_crud
from .follow_schema import (
    FollowResponse,
    FollowStatusUpdate,
    FollowersResponse,
    FollowerItem,
    FollowingResponse,
    FollowingItem,
    FollowRequestsResponse,
    FollowRequestItem,
    FollowRequestUserBrief,
)

follow_router = APIRouter(prefix='/api/users', tags=['follow'])


@follow_router.post('/{user_id}/follow', response_model=FollowResponse, status_code=status.HTTP_201_CREATED)
async def follow_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Follow a user. Status depends on target user's privacy settings."""
    # Can't follow yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Cannot follow yourself'
        )

    # Check target user exists
    target_user = user_crud.get_user_by_id(db, user_id)
    if not target_user or not target_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found'
        )

    # Check if already following (including rejected)
    existing_follow = follow_crud.get_follow(db, current_user.id, user_id)
    if existing_follow:
        if existing_follow.status == FollowStatus.REJECTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Follow request was rejected'
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Already following or request pending'
        )

    # Determine initial status based on privacy
    initial_status = follow_crud.get_initial_follow_status(target_user)

    # Create follow
    follow = follow_crud.create_follow(db, current_user.id, user_id, initial_status)

    return follow


@follow_router.patch('/follow-requests/{follow_id}', status_code=status.HTTP_200_OK)
async def update_follow_request(
    follow_id: int,
    update: FollowStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Accept or reject a follow request. Only target user can do this."""
    follow = follow_crud.get_follow_by_id(db, follow_id)
    if not follow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Follow request not found'
        )

    # Only target user can accept/reject
    if follow.following_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only the target user can accept or reject follow requests'
        )

    # Can only update pending requests
    if follow.status != FollowStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Can only update pending follow requests'
        )

    # Validate status
    if update.status not in [FollowStatus.ACCEPTED, FollowStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Status must be accepted or rejected'
        )

    follow_crud.update_follow_status(db, follow, update.status)

    return {'status': 'ok'}


@follow_router.delete('/{user_id}/follow', status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unfollow a user. Hard delete allows re-following later."""
    follow = follow_crud.get_follow(db, current_user.id, user_id)
    if not follow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Not following this user'
        )

    follow_crud.delete_follow(db, follow)
    return None


@follow_router.get('/{user_id}/followers', response_model=FollowersResponse)
async def get_followers(
    user_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """List user's followers. Only accepted followers are shown."""
    # Check user exists
    target_user = user_crud.get_user_by_id(db, user_id)
    if not target_user or not target_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found'
        )

    follows, total = follow_crud.get_followers(db, user_id, limit, offset)

    followers = []
    for follow in follows:
        follower = follow.follower
        # Check if current user is following this follower
        is_following = None
        if current_user:
            is_following = follow_crud.is_following(db, current_user.id, follower.id)

        followers.append(FollowerItem(
            id=follower.id,
            username_display=follower.username_display,
            first_name=follower.first_name,
            last_name=follower.last_name,
            logo=follower.logo,
            is_following=is_following,
        ))

    return FollowersResponse(
        followers=followers,
        total=total,
        limit=limit,
        offset=offset,
    )


@follow_router.get('/{user_id}/following', response_model=FollowingResponse)
async def get_following(
    user_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """List who user follows. Self sees all statuses, others see only accepted."""
    # Check user exists
    target_user = user_crud.get_user_by_id(db, user_id)
    if not target_user or not target_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found'
        )

    # Self can see all statuses
    is_self = current_user and current_user.id == user_id
    follows, total = follow_crud.get_following(db, user_id, include_pending=is_self, limit=limit, offset=offset)

    following = []
    for follow in follows:
        followed_user = follow.following

        # Determine status to show
        show_status = None
        if is_self:
            # Mask rejected as pending
            if follow.status == FollowStatus.REJECTED:
                show_status = FollowStatus.PENDING
            else:
                show_status = follow.status

        following.append(FollowingItem(
            id=followed_user.id,
            username_display=followed_user.username_display,
            first_name=followed_user.first_name,
            last_name=followed_user.last_name,
            logo=followed_user.logo,
            status=show_status,
        ))

    return FollowingResponse(
        following=following,
        total=total,
        limit=limit,
        offset=offset,
    )


@follow_router.get('/me/follow-requests', response_model=FollowRequestsResponse)
async def get_pending_follow_requests(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get pending follow requests awaiting approval."""
    requests, total = follow_crud.get_pending_follow_requests(
        db, current_user.id, limit, offset
    )

    result = []
    for req in requests:
        follower = req.follower
        result.append(FollowRequestItem(
            id=req.id,
            follower=FollowRequestUserBrief(
                id=follower.id,
                username_display=follower.username_display,
                first_name=follower.first_name,
                last_name=follower.last_name,
                logo=follower.logo,
            ),
            created_at=req.created_at,
        ))

    return FollowRequestsResponse(
        requests=result,
        total=total,
        limit=limit,
        offset=offset,
    )
