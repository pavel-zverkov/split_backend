from datetime import datetime

from pydantic import BaseModel
from ..enums.artifact_kind import ArtifactKind


class ArtifactCreate(BaseModel):
    file_name: str
    file_path: str | None = None
    kind: ArtifactKind
    tags: str | None = None
    competition_id: int | None = None
    user_id: int | None = None

    model_config = {'from_attributes': True}


class Artifact(ArtifactCreate):
    id: int

    model_config = {'from_attributes': True}
