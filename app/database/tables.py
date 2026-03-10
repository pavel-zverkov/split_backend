# Core entities
from ..user.user_model import User
from ..workout.workout_model import Workout
from ..workout.workout_split_model import WorkoutSplit
from ..event.event_model import Event
from ..competition.competition_model import Competition
from ..artifact.artifact_model import Artifact
from ..artifact.orient.maps.orient_map_model import OrientMap
from ..club.club_model import Club
from ..competition.distance_model import Distance
from ..competition.control_point_model import ControlPoint
from ..result.result_model import Result
from ..result.result_split_model import ResultSplit

# Relation entities (junction tables)
from ..user.user_follow_model import UserFollow
from ..user.claim_request_model import ClaimRequest
from ..user.user_qualification_model import UserQualification
from ..club.club_membership_model import ClubMembership
from ..event.event_invite_model import EventInvite
from ..event.event_participation_model import EventParticipation
from ..event.total_config_model import EventTotalConfig
from ..event.total_result_model import EventTotalResult
from ..competition.competition_team_model import CompetitionTeam
from ..competition.competition_registration_model import CompetitionRegistration

# Child entities
from ..spectator.spectator_session_model import SpectatorSession

__all__ = [
    # Core
    'User',
    'Workout',
    'WorkoutSplit',
    'Event',
    'Competition',
    'Distance',
    'ControlPoint',
    'Artifact',
    'OrientMap',
    'Club',
    'Result',
    'ResultSplit',
    # Relations
    'UserFollow',
    'ClaimRequest',
    'UserQualification',
    'ClubMembership',
    'EventInvite',
    'EventParticipation',
    'EventTotalConfig',
    'EventTotalResult',
    'CompetitionTeam',
    'CompetitionRegistration',
    # Child
    'SpectatorSession',
]
