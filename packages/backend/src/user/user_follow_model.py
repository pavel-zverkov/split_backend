from sqlalchemy import (Column,
                        DateTime,
                        Enum,
                        ForeignKey,
                        Integer,
                        UniqueConstraint,
                        func)
from sqlalchemy.orm import relationship

from ..database import Base
from ..enums.follow_status import FollowStatus


class UserFollow(Base):
    """
    Represents a follow relationship between two users.

    A user (follower) can follow another user (following). The follow request
    may require approval depending on the target user's privacy settings.
    Rejection is hidden from the follower (shown as 'pending').

    Attributes:
        follower_id: The user who initiates the follow.
        following_id: The user being followed.
        status: pending | accepted | rejected.
    """
    __tablename__ = 'user_follows'

    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    following_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(Enum(FollowStatus), nullable=False, default=FollowStatus.PENDING)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('follower_id', 'following_id', name='user_follow_unique'),
    )

    # Relationships
    follower = relationship('User', foreign_keys=[follower_id])
    following = relationship('User', foreign_keys=[following_id])
