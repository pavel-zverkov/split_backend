from enum import Enum


class ArtifactKind(Enum):
    # Competition artifacts
    MAP = 'map'
    COURSE = 'course'
    RESULTS_FILE = 'results_file'
    PHOTO = 'photo'
    # Workout artifacts
    GPS_TRACK = 'gps_track'
    FIT_FILE = 'fit_file'
    TCX_FILE = 'tcx_file'
