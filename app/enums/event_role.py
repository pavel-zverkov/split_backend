from enum import Enum


class EventRole(Enum):
    ORGANIZER = 'organizer'
    SECRETARY = 'secretary'
    JUDGE = 'judge'
    VOLUNTEER = 'volunteer'
    PARTICIPANT = 'participant'
    SPECTATOR = 'spectator'
