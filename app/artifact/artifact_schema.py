from datetime import datetime

from pydantic import BaseModel, Field

from ..enums.artifact_kind import ArtifactKind


# ===== User Brief =====

class ArtifactUserBrief(BaseModel):
    id: int
    username_display: str

    model_config = {'from_attributes': True}


# ===== Request Schemas =====

class ArtifactUpdate(BaseModel):
    tags: list[str] | None = None
    kind: ArtifactKind | None = None


# ===== Response Schemas =====

class ArtifactResponse(BaseModel):
    id: int
    competition_id: int | None = None
    workout_id: int | None = None
    user_id: int
    kind: ArtifactKind
    file_path: str
    file_name: str
    file_size: int
    mime_type: str
    tags: list[str] | None = None
    created_at: datetime

    model_config = {'from_attributes': True}


class ArtifactListItem(BaseModel):
    id: int
    kind: ArtifactKind
    file_name: str
    file_size: int
    mime_type: str
    tags: list[str] | None = None
    uploaded_by: ArtifactUserBrief
    created_at: datetime

    model_config = {'from_attributes': True}


class ArtifactDetailResponse(BaseModel):
    id: int
    competition_id: int | None = None
    workout_id: int | None = None
    kind: ArtifactKind
    file_path: str
    file_name: str
    file_size: int
    mime_type: str
    tags: list[str] | None = None
    uploaded_by: ArtifactUserBrief
    download_url: str | None = None
    created_at: datetime

    model_config = {'from_attributes': True}


class ArtifactsListResponse(BaseModel):
    artifacts: list[ArtifactListItem]
    total: int
    limit: int
    offset: int


# ===== File Validation Config =====

COMPETITION_ARTIFACT_KINDS = {ArtifactKind.MAP, ArtifactKind.COURSE, ArtifactKind.RESULTS_FILE, ArtifactKind.PHOTO}
WORKOUT_ARTIFACT_KINDS = {ArtifactKind.GPS_TRACK, ArtifactKind.FIT_FILE, ArtifactKind.TCX_FILE}

FILE_VALIDATION = {
    ArtifactKind.MAP: {
        'extensions': {'jpg', 'jpeg', 'png', 'pdf'},
        'max_size': 50 * 1024 * 1024,  # 50 MB
    },
    ArtifactKind.COURSE: {
        'extensions': {'ocd', 'xml', 'ppn'},
        'max_size': 10 * 1024 * 1024,  # 10 MB
    },
    ArtifactKind.RESULTS_FILE: {
        'extensions': {'csv', 'xml', 'json'},
        'max_size': 5 * 1024 * 1024,  # 5 MB
    },
    ArtifactKind.PHOTO: {
        'extensions': {'jpg', 'jpeg', 'png'},
        'max_size': 20 * 1024 * 1024,  # 20 MB
    },
    ArtifactKind.GPS_TRACK: {
        'extensions': {'gpx'},
        'max_size': 10 * 1024 * 1024,  # 10 MB
    },
    ArtifactKind.FIT_FILE: {
        'extensions': {'fit'},
        'max_size': 20 * 1024 * 1024,  # 20 MB
    },
    ArtifactKind.TCX_FILE: {
        'extensions': {'tcx'},
        'max_size': 10 * 1024 * 1024,  # 10 MB
    },
}

MIME_TYPES = {
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'pdf': 'application/pdf',
    'ocd': 'application/octet-stream',
    'xml': 'application/xml',
    'ppn': 'application/octet-stream',
    'csv': 'text/csv',
    'json': 'application/json',
    'gpx': 'application/gpx+xml',
    'fit': 'application/vnd.ant.fit',
    'tcx': 'application/vnd.garmin.tcx+xml',
}
