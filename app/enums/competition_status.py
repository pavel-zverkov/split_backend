from enum import Enum


class CompetitionStatus(Enum):
    PLANNED = 'planned'
    REGISTRATION_OPEN = 'registration_open'
    REGISTRATION_CLOSED = 'registration_closed'
    IN_PROGRESS = 'in_progress'
    FINISHED = 'finished'
    CANCELLED = 'cancelled'
