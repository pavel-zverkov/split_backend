import re
from typing import Any
from fastapi import (APIRouter,
                     Depends,
                     HTTPException)
import requests
from sqlalchemy.orm import Session


from ..competition.competition_pydantic_model import Competition
from ..event.event_pydantic_model import Event

from ..artifact.orient.maps.orient_map_controller import create_omap
from ..artifact.orient.maps.orient_map_pydantic_model import OrientMapCreate

from ..database.minio_integration import get_minio_client
from ..competition.competition_crud import get_competition
from ..event.event_crud import get_event
from ..enums.enum_artifact_kind import ArtifactKind

from ..database import get_db
from ..logger import logger
from . import artifact_crud
from .artifact_pydantic_model import Artifact, ArtifactCreate

BUCKET_NAME = 'event-artifacts'

artifact_router = APIRouter()


@artifact_router.get(
    "/artifact/",
    tags=["artifacts"],
    response_model=Artifact
)
async def read_artifact(
    artifact_name: str,
    db: Session = Depends(get_db)
) -> Artifact | None:
    artifact = artifact_crud.get_artifact_by_name(db, artifact_name)
    return artifact


@artifact_router.post(
    "/artifact/",
    tags=["artifacts"],
    response_model=Artifact
)
async def create_artifact(
    artifact_url: str,
    artifact_params: ArtifactCreate,
    artifact_kind_spec: dict[str, Any],
    db: Session = Depends(get_db),
    # TODO: change to sqlalchemy-file lib
    # artifact_db: Minio = get_minio_client()
    # artifact: Union[UploadFile, None] = None,
) -> Artifact | None:

    # TODO: Необходимо доделать как транзакцию, чтобы при падении create artifact_spec или save_artifact откатывались операции create
    db_artifact = artifact_crud.get_artifact_by_name(db, artifact_params.file_name, artifact_params.competition)
    if db_artifact:
        raise HTTPException(status_code=400, detail=f"Artifact {artifact_params.file_name} already registered")

    artifact_kind_spec['competition'] = get_competition(db, artifact_params.competition)
    artifact_kind_spec['event'] = get_event(db, artifact_kind_spec['competition'].event)
    artifact_params.file_path = _get_path(artifact_kind_spec, artifact_params.file_name)

    artifact = artifact_crud.create_artifact(db=db, artifact=artifact_params)

    await create_artifact_spec(
        db=db,
        artifact=artifact,
        artifact_kind_spec=artifact_kind_spec
    )

    await save_artifact(
        artifact_url=artifact_url,
        path=artifact_params.file_path,
        tags=artifact.tags
    )

    return artifact


async def save_artifact(
    artifact_url: str, 
    path: str, 
    bucket: str = BUCKET_NAME, 
    tags: str | None = None
) -> None:
    minio_client = get_minio_client()
    # Необходимо лучше продумать названия и структуру хранения файлов
    if not minio_client.bucket_exists(bucket):
        minio_client.make_bucket(bucket)

    with requests.get(artifact_url, stream=True, timeout=10) as r:
        r.raise_for_status()
        content_length = int(r.headers["Content-Length"])

        minio_client.put_object(
            bucket_name=bucket,
            object_name=path,
            data=r.raw,
            length=content_length,
        )

        logger.success('Save artifact to minio')

        return


async def create_artifact_spec(db: Session, artifact: Artifact, artifact_kind_spec: dict[str, Any]) -> None:

    if artifact.kind == ArtifactKind.O_MAP:
        competition: Competition = artifact_kind_spec.get('competition')

        orient_map_create = OrientMapCreate(
            artifact=artifact.id,
            map_name=artifact.file_name,
            location_name=competition.location,
            location_point=artifact_kind_spec.get('location_point')
        )

        await create_omap(db, orient_map_create)


def _transform_event_name(event_name: str) -> str:
    return re.sub(r"[0-9]+", '', event_name)


def _get_path(artifact_kind_spec: dict[str, Any], file_name: str) -> str:
    competition: Competition = artifact_kind_spec.get('competition')
    event: Event = artifact_kind_spec.get('event')

    return f'{_transform_event_name(event.name)}/{competition.date}/{competition.name}/{file_name}'
