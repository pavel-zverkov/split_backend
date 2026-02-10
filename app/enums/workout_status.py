from enum import Enum


class WorkoutStatus(Enum):
    DRAFT = 'draft'
    PROCESSING = 'processing'
    READY = 'ready'
    ERROR = 'error'
