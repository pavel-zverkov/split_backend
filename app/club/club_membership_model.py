from sqlalchemy import (Column,
                        DateTime,
                        Enum,
                        ForeignKey,
                        Integer,
                        UniqueConstraint,
                        func)
from sqlalchemy.orm import relationship

from ..database import Base
from ..enums.club_role import ClubRole
from ..enums.membership_status import MembershipStatus


class ClubMembership(Base):
    """
    Represents a user's membership in a club.

    Users can join clubs as members, coaches, or owners. For 'by_request' clubs,
    membership requires approval. Rejection is hidden (shown as 'pending').

    Attributes:
        user_id: The member.
        club_id: The club.
        role: owner | coach | member.
        status: pending | active | rejected.
        joined_at: When membership was approved.
    """
    __tablename__ = 'club_memberships'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    club_id = Column(Integer, ForeignKey('clubs.id'), nullable=False)
    role = Column(Enum(ClubRole), nullable=False, default=ClubRole.MEMBER)
    status = Column(Enum(MembershipStatus), nullable=False, default=MembershipStatus.PENDING)
    joined_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'club_id', name='club_membership_unique'),
    )

    # Relationships
    user = relationship('User')
    club = relationship('Club', back_populates='memberships')
