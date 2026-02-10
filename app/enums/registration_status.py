from enum import Enum


class RegistrationStatus(Enum):
    PENDING = 'pending'
    REGISTERED = 'registered'
    CONFIRMED = 'confirmed'
    REJECTED = 'rejected'
