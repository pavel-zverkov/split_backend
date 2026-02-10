from enum import Enum


class MembershipStatus(Enum):
    PENDING = 'pending'
    ACTIVE = 'active'
    REJECTED = 'rejected'
