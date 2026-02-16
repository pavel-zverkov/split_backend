from sqlalchemy import (Column,
                        DateTime,
                        Enum,
                        ForeignKey,
                        Integer,
                        func)
from sqlalchemy.orm import relationship

from ..database import Base
from ..enums.claim_status import ClaimStatus
from ..enums.claim_type import ClaimType


class ClaimRequest(Base):
    """
    Represents a request to claim a ghost user account.

    Attributes:
        claimer_id: Registered user claiming the ghost account.
        ghost_user_id: Ghost user being claimed.
        approver_id: Who must approve (claimer for event, ghost creator for club).
        claim_type: 'event' (self-approved) or 'club' (owner-approved).
        status: pending | approved | rejected.
        resolved_at: When the claim was approved/rejected.
    """
    __tablename__ = 'claim_requests'

    id = Column(Integer, primary_key=True, index=True)
    claimer_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    ghost_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    approver_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    claim_type = Column(Enum(ClaimType), nullable=False, default=ClaimType.EVENT)
    status = Column(Enum(ClaimStatus), nullable=False, default=ClaimStatus.PENDING)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    claimer = relationship('User', foreign_keys=[claimer_id])
    ghost_user = relationship('User', foreign_keys=[ghost_user_id])
    approver = relationship('User', foreign_keys=[approver_id])
