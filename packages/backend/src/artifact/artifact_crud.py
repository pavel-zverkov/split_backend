from datetime import date

from sqlalchemy.orm import Session

from .artifact_orm_model import Artifact
from .artifact_pydantic_model import ArtifactCreate


from .orient.maps.orient_map_crud import create_omap

from ..logger import logger

# def get_user(db: Session, mobile_number: str) -> None:
#     return db.query(User).filter(User.mobile_number == mobile_number).first()


def get_artifact(db: Session, artifact_id: int) -> Artifact | None:
    return db.query(Artifact).filter(Artifact.id == artifact_id).first()


def get_artifact_by_name(db: Session, file_name: str, competition_id: int) -> Artifact | None:
    return db.query(Artifact).filter(Artifact.file_name == file_name, Artifact.competition == competition_id).first()


def create_artifact(
    db: Session,
    artifact: ArtifactCreate,
) -> Artifact:

    db_artifact = Artifact(**artifact.model_dump())
    db.add(db_artifact)
    db.commit()
    db.refresh(db_artifact)

    logger.success(f'Create artifact {artifact.model_dump()}')

    return db_artifact

# TODO: update_artifact, delete_artifact
