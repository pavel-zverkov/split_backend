from enum import Enum


class EventStatus(Enum):
    DRAFT = 'draft'
    PLANNED = 'planned'
    REGISTRATION_OPEN = 'registration_open'
    IN_PROGRESS = 'in_progress'
    FINISHED = 'finished'
    CANCELLED = 'cancelled'
