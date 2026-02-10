from enum import Enum


class CompetitionStatus(Enum):
    PLANNED = 'planned'
    IN_PROGRESS = 'in_progress'
    FINISHED = 'finished'
    CANCELLED = 'cancelled'
