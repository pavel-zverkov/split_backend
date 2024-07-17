from datetime import datetime

from pydantic import BaseModel
from ..enums.enum_artifact_kind import ArtifactKind


class ArtifactCreate(BaseModel):
    file_name: str
    file_path: str | None = None
    kind: ArtifactKind = ArtifactKind.SIMPLE
    tags: str | None = None
    competition: int | None = None
    uploader: int | None = None
    upload_ts: datetime = datetime.now()


class Artifact(ArtifactCreate):
    id: int
