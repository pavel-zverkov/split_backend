from enum import Enum


class EventStatus(Enum):
    DRAFT = 'draft'
    PLANNED = 'planned'
    IN_PROGRESS = 'in_progress'
    FINISHED = 'finished'
    CANCELLED = 'cancelled'
