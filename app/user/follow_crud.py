from sqlalchemy import or_
from sqlalchemy.orm import Session

from .user_model import User
from .user_follow_model import UserFollow
from ..enums.follow_status import FollowStatus
from ..enums.privacy import Privacy


def get_follow(db: Session, follower_id: int, following_id: int) -> UserFollow | None:
    return db.query(UserFollow).filter(
        UserFollow.follower_id == follower_id,
        UserFollow.following_id == following_id
    ).first()


def get_follow_by_id(db: Session, follow_id: int) -> UserFollow | None:
    return db.query(UserFollow).filter(UserFollow.id == follow_id).first()


def create_follow(db: Session, follower_id: int, following_id: int, status: FollowStatus) -> UserFollow:
    follow = UserFollow(
        follower_id=follower_id,
        following_id=following_id,
        status=status,
    )
    db.add(follow)
    db.commit()
    db.refresh(follow)
    return follow


def update_follow_status(db: Session, follow: UserFollow, status: FollowStatus) -> UserFollow:
    follow.status = status
    db.commit()
    db.refresh(follow)
    return follow


def delete_follow(db: Session, follow: UserFollow) -> None:
    db.delete(follow)
    db.commit()


def get_initial_follow_status(target_user: User) -> FollowStatus:
    """Determine initial follow status based on target user's privacy settings."""
    if target_user.privacy_default == Privacy.PUBLIC:
        return FollowStatus.ACCEPTED
    return FollowStatus.PENDING


def get_followers(
    db: Session,
    user_id: int,
    limit: int = 20,
    offset: int = 0
) -> tuple[list[UserFollow], int]:
    q = db.query(UserFollow).filter(
        UserFollow.following_id == user_id,
        UserFollow.status == FollowStatus.ACCEPTED
    )
    total = q.count()
    follows = q.offset(offset).limit(limit).all()
    return follows, total


def get_following(
    db: Session,
    user_id: int,
    include_pending: bool = False,
    limit: int = 20,
    offset: int = 0
) -> tuple[list[UserFollow], int]:
    q = db.query(UserFollow).filter(UserFollow.follower_id == user_id)

    if include_pending:
        # For self - show all statuses (but rejected appears as pending to UI)
        q = q.filter(
            UserFollow.status.in_([
                FollowStatus.ACCEPTED,
                FollowStatus.PENDING,
                FollowStatus.REJECTED
            ])
        )
    else:
        # For others - only show accepted
        q = q.filter(UserFollow.status == FollowStatus.ACCEPTED)

    total = q.count()
    follows = q.offset(offset).limit(limit).all()
    return follows, total


def get_pending_follow_requests(
    db: Session,
    user_id: int,
    limit: int = 20,
    offset: int = 0
) -> tuple[list[UserFollow], int]:
    q = db.query(UserFollow).filter(
        UserFollow.following_id == user_id,
        UserFollow.status == FollowStatus.PENDING
    )
    total = q.count()
    requests = q.offset(offset).limit(limit).all()
    return requests, total


def is_following(db: Session, follower_id: int, following_id: int) -> bool:
    follow = db.query(UserFollow).filter(
        UserFollow.follower_id == follower_id,
        UserFollow.following_id == following_id,
        UserFollow.status == FollowStatus.ACCEPTED
    ).first()
    return follow is not None
