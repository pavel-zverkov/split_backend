from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth.auth_service import get_current_user, get_current_user_optional, hash_password, verify_password
from ..enums.account_type import AccountType
from . import user_crud
from .user_model import User
from .user_schema import (
    UserResponse,
    UserPublicProfile,
    UserUpdate,
    PasswordChange,
    UserSearchResponse,
    UserSearchItem,
    GhostUserCreate,
    GhostUserResponse,
    GhostMatchResponse,
    GhostMatchItem,
    GhostMatchEventInfo,
    GhostMatchCompetitionInfo,
    GhostMatchClubInfo,
    CreatorBrief,
    AvatarResponse,
)

user_router = APIRouter(prefix='/api/users', tags=['users'])


@user_router.get('/me', response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user


@user_router.patch('/me', response_model=UserResponse)
async def update_current_user_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check email uniqueness if being updated
    if update_data.email and update_data.email != current_user.email:
        existing = user_crud.get_user_by_email(db, update_data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Email already in use'
            )

    updated_user = user_crud.update_user(db, current_user, update_data)

    # Check for warnings
    warnings = []
    birthday = update_data.birthday or updated_user.birthday
    if birthday:
        age = (date.today() - birthday).days // 365
        if age < 10:
            warnings.append(f'Age is {age} years. Please verify birthday is correct.')

    return UserResponse(
        id=updated_user.id,
        username=updated_user.username,
        username_display=updated_user.username_display,
        email=updated_user.email,
        first_name=updated_user.first_name,
        last_name=updated_user.last_name,
        birthday=updated_user.birthday,
        gender=updated_user.gender,
        logo=updated_user.logo,
        bio=updated_user.bio,
        privacy_default=updated_user.privacy_default,
        account_type=updated_user.account_type,
        created_at=updated_user.created_at,
        warnings=warnings if warnings else None,
    )


@user_router.patch('/me/password', status_code=status.HTTP_200_OK)
async def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Cannot change password for this account'
        )

    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Current password is incorrect'
        )

    current_user.password_hash = hash_password(data.new_password)
    db.commit()

    return {'status': 'ok'}


@user_router.post('/me/avatar', response_model=AvatarResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/webp']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='File must be JPEG, PNG, or WebP image'
        )

    # Validate file size (5MB)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='File size must be less than 5MB'
        )

    # Upload to MinIO
    from ..database.minio_service import upload_avatar
    logo_url = upload_avatar(current_user.id, contents, file.content_type)
    current_user.logo = logo_url
    db.commit()

    return AvatarResponse(logo=logo_url)


@user_router.delete('/me', status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    hard: bool = Query(False, description='GDPR hard delete'),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if user owns clubs
    if user_crud.user_owns_clubs(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Transfer club ownership first'
        )

    # Check if user organizes active events
    if user_crud.user_organizes_active_events(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Transfer event ownership first'
        )

    # Delete related records
    user_crud.delete_user_follows(db, current_user.id)
    user_crud.delete_user_club_memberships(db, current_user.id)
    user_crud.delete_pending_claim_requests(db, current_user.id)

    # Soft or hard delete
    if hard:
        # Delete avatar from MinIO
        from ..database.minio_service import delete_avatar
        delete_avatar(current_user.id)
        user_crud.hard_delete_user(db, current_user)
    else:
        user_crud.soft_delete_user(db, current_user)

    return None


@user_router.get('/{user_id}', response_model=UserPublicProfile)
async def get_public_profile(
    user_id: int,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    user = user_crud.get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found'
        )

    # Get follow status if authenticated
    follow_status = None
    if current_user and current_user.id != user_id:
        follow_status = user_crud.get_follow_status(db, current_user.id, user_id)

    # Truncate last name for privacy (unless follower)
    last_name = user.last_name
    if last_name and (not current_user or follow_status is None):
        last_name = f"{last_name[0]}." if last_name else None

    return UserPublicProfile(
        id=user.id,
        username_display=user.username_display,
        first_name=user.first_name,
        last_name=last_name,
        logo=user.logo,
        bio=user.bio,
        account_type=user.account_type,
        follow_status=follow_status,
        followers_count=user_crud.get_followers_count(db, user_id),
        following_count=user_crud.get_following_count(db, user_id),
        workouts_count=user_crud.get_workouts_count(db, user_id),
    )


@user_router.get('', response_model=UserSearchResponse)
async def search_users(
    q: str | None = Query(None, description='Search query'),
    account_type: AccountType | None = Query(None, description='Filter by account type'),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    users, total = user_crud.search_users(db, q, account_type, limit, offset)

    return UserSearchResponse(
        users=[
            UserSearchItem(
                id=u.id,
                username_display=u.username_display,
                first_name=u.first_name,
                last_name=f"{u.last_name[0]}." if u.last_name else None,
                account_type=u.account_type,
            )
            for u in users
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@user_router.post('/ghost', response_model=GhostUserResponse, status_code=status.HTTP_201_CREATED)
async def create_ghost_user(
    data: GhostUserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check permission
    if not user_crud.can_create_ghost_users(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only club owners/coaches or event organizers can create ghost users'
        )

    ghost_user = user_crud.create_ghost_user(db, data, current_user.id)

    return GhostUserResponse(
        id=ghost_user.id,
        username=ghost_user.username,
        username_display=ghost_user.username_display,
        first_name=ghost_user.first_name,
        last_name=ghost_user.last_name,
        account_type=ghost_user.account_type,
        created_by=ghost_user.created_by,
    )


@user_router.get('/me/find-history', response_model=GhostMatchResponse)
async def find_matching_ghosts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    matches = user_crud.find_matching_ghosts(
        db,
        current_user.first_name,
        current_user.last_name,
        current_user.birthday,
    )

    result = []
    for ghost in matches:
        creator = None
        if ghost.created_by:
            creator_user = user_crud.get_user_by_id(db, ghost.created_by)
            if creator_user:
                creator = CreatorBrief(
                    id=creator_user.id,
                    username_display=creator_user.username_display,
                )

        competitions_count = user_crud.get_user_competitions_count(db, ghost.id)
        results_summary = user_crud.get_user_results_summary(db, ghost.id)

        # Get events and clubs for this ghost
        events_raw = user_crud.get_ghost_events(db, ghost.id)
        events = [
            GhostMatchEventInfo(
                event_id=e['event_id'],
                event_name=e['event_name'],
                competitions=[
                    GhostMatchCompetitionInfo(**c) for c in e['competitions']
                ],
            ) for e in events_raw
        ]

        clubs_raw = user_crud.get_ghost_clubs(db, ghost.id)
        clubs = [GhostMatchClubInfo(**c) for c in clubs_raw]

        result.append(GhostMatchItem(
            user_id=ghost.id,
            username_display=ghost.username_display,
            first_name=ghost.first_name,
            last_name=ghost.last_name,
            birthday=ghost.birthday,
            created_by=creator,
            competitions_count=competitions_count,
            results_summary=results_summary,
            events=events,
            clubs=clubs,
        ))

    return GhostMatchResponse(matches=result)
