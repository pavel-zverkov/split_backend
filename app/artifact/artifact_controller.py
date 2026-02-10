from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..database.minio_integration import get_minio_client
from ..auth.auth_service import get_current_user, get_current_user_optional
from ..user.user_model import User
from ..competition.competition_crud import get_competition
from ..workout.workout_crud import get_workout
from ..enums.artifact_kind import ArtifactKind
from . import artifact_crud
from .artifact_schema import (
    ArtifactResponse,
    ArtifactDetailResponse,
    ArtifactListItem,
    ArtifactsListResponse,
    ArtifactUserBrief,
    ArtifactUpdate,
    COMPETITION_ARTIFACT_KINDS,
    WORKOUT_ARTIFACT_KINDS,
    FILE_VALIDATION,
    MIME_TYPES,
)

artifact_router = APIRouter(tags=['artifacts'])

BUCKET_NAME = 'event-artifacts'


# ===== Helper Functions =====

def get_competition_or_404(db: Session, competition_id: int):
    competition = get_competition(db, competition_id)
    if not competition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Competition not found'
        )
    return competition


def get_workout_or_404(db: Session, workout_id: int):
    workout = get_workout(db, workout_id)
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Workout not found'
        )
    return workout


def get_artifact_or_404(db: Session, artifact_id: int):
    artifact = artifact_crud.get_artifact(db, artifact_id)
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Artifact not found'
        )
    return artifact


def validate_file(file: UploadFile, kind: ArtifactKind) -> tuple[str, str]:
    """Validate file extension and size. Returns (extension, mime_type)."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Filename is required'
        )

    extension = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    validation = FILE_VALIDATION.get(kind)

    if not validation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Unknown artifact kind: {kind}'
        )

    if extension not in validation['extensions']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid file type for {kind.value}. Allowed: {", ".join(validation["extensions"])}'
        )

    mime_type = MIME_TYPES.get(extension, 'application/octet-stream')
    return extension, mime_type


async def upload_to_minio(file: UploadFile, path: str, max_size: int) -> int:
    """Upload file to MinIO. Returns file size."""
    minio_client = get_minio_client()

    if not minio_client.bucket_exists(BUCKET_NAME):
        minio_client.make_bucket(BUCKET_NAME)

    # Read file content
    content = await file.read()
    file_size = len(content)

    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'File too large. Maximum size: {max_size // (1024*1024)} MB'
        )

    minio_client.put_object(
        bucket_name=BUCKET_NAME,
        object_name=path,
        data=BytesIO(content),
        length=file_size,
    )

    return file_size


def delete_from_minio(path: str) -> None:
    """Delete file from MinIO."""
    minio_client = get_minio_client()
    try:
        minio_client.remove_object(BUCKET_NAME, path)
    except Exception:
        pass  # Ignore if file doesn't exist


def get_presigned_url(path: str) -> str:
    """Get presigned download URL from MinIO."""
    from datetime import timedelta
    minio_client = get_minio_client()
    return minio_client.presigned_get_object(BUCKET_NAME, path, expires=timedelta(hours=1))


def build_artifact_list_item(artifact, user: User) -> ArtifactListItem:
    return ArtifactListItem(
        id=artifact.id,
        kind=artifact.kind,
        file_name=artifact.file_name,
        file_size=artifact.file_size,
        mime_type=artifact.mime_type,
        tags=artifact.tags,
        uploaded_by=ArtifactUserBrief(
            id=user.id,
            username_display=user.username_display,
        ),
        created_at=artifact.created_at,
    )


# ===== 10.1 Upload Competition Artifact =====

@artifact_router.post('/api/competitions/{competition_id}/artifacts', response_model=ArtifactResponse, status_code=status.HTTP_201_CREATED)
async def upload_competition_artifact(
    competition_id: int,
    file: Annotated[UploadFile, File()],
    kind: Annotated[ArtifactKind, Form()],
    tags: Annotated[str | None, Form()] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a competition artifact (organizer/secretary only)."""
    competition = get_competition_or_404(db, competition_id)

    # Check permissions
    if not artifact_crud.can_upload_competition_artifact(db, current_user.id, competition.event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer or secretary can upload artifacts'
        )

    # Validate artifact kind
    if kind not in COMPETITION_ARTIFACT_KINDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid kind for competition artifact. Allowed: {", ".join(k.value for k in COMPETITION_ARTIFACT_KINDS)}'
        )

    # Validate file
    extension, mime_type = validate_file(file, kind)
    validation = FILE_VALIDATION[kind]

    # Build file path
    file_path = f'events/{competition.event_id}/{competition_id}/{kind.value}/{file.filename}'

    # Upload to MinIO
    file_size = await upload_to_minio(file, file_path, validation['max_size'])

    # Parse tags
    tags_list = [t.strip() for t in tags.split(',')] if tags else None

    # Create artifact record
    artifact = artifact_crud.create_artifact(
        db,
        user_id=current_user.id,
        kind=kind,
        file_path=file_path,
        file_name=file.filename,
        file_size=file_size,
        mime_type=mime_type,
        competition_id=competition_id,
        tags=tags_list,
    )

    return ArtifactResponse(
        id=artifact.id,
        competition_id=artifact.competition_id,
        workout_id=artifact.workout_id,
        user_id=artifact.user_id,
        kind=artifact.kind,
        file_path=artifact.file_path,
        file_name=artifact.file_name,
        file_size=artifact.file_size,
        mime_type=artifact.mime_type,
        tags=artifact.tags,
        created_at=artifact.created_at,
    )


# ===== 10.2 List Competition Artifacts =====

@artifact_router.get('/api/competitions/{competition_id}/artifacts', response_model=ArtifactsListResponse)
async def list_competition_artifacts(
    competition_id: int,
    kind: ArtifactKind | None = None,
    tags: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List competition artifacts (public)."""
    competition = get_competition_or_404(db, competition_id)

    # Parse tags
    tags_list = [t.strip() for t in tags.split(',')] if tags else None

    artifacts, total = artifact_crud.get_competition_artifacts(
        db, competition_id,
        kind=kind,
        tags=tags_list,
        limit=limit,
        offset=offset
    )

    # Get user info for each artifact
    from ..user.user_crud import get_user
    items = []
    for artifact in artifacts:
        user = get_user(db, artifact.user_id)
        if user:
            items.append(build_artifact_list_item(artifact, user))

    return ArtifactsListResponse(
        artifacts=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# ===== 10.3 Get Artifact Details =====

@artifact_router.get('/api/artifacts/{artifact_id}', response_model=ArtifactDetailResponse)
async def get_artifact_details(
    artifact_id: int,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Get artifact details."""
    artifact = get_artifact_or_404(db, artifact_id)

    # Check visibility for workout artifacts
    if artifact.workout_id:
        workout = get_workout(db, artifact.workout_id)
        if workout and not artifact_crud.can_view_workout_artifact(
            db, current_user.id if current_user else None, workout.user_id, workout.privacy
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Private workout artifact'
            )

    # Get uploader info
    from ..user.user_crud import get_user
    user = get_user(db, artifact.user_id)

    # Get download URL
    download_url = get_presigned_url(artifact.file_path)

    return ArtifactDetailResponse(
        id=artifact.id,
        competition_id=artifact.competition_id,
        workout_id=artifact.workout_id,
        kind=artifact.kind,
        file_path=artifact.file_path,
        file_name=artifact.file_name,
        file_size=artifact.file_size,
        mime_type=artifact.mime_type,
        tags=artifact.tags,
        uploaded_by=ArtifactUserBrief(
            id=user.id,
            username_display=user.username_display,
        ) if user else None,
        download_url=download_url,
        created_at=artifact.created_at,
    )


# ===== 10.4 Update Artifact =====

@artifact_router.patch('/api/artifacts/{artifact_id}', response_model=ArtifactResponse)
async def update_artifact(
    artifact_id: int,
    data: ArtifactUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update artifact metadata."""
    artifact = get_artifact_or_404(db, artifact_id)

    # Check permissions
    if artifact.competition_id:
        competition = get_competition(db, artifact.competition_id)
        if not competition or not artifact_crud.can_manage_competition_artifact(
            db, current_user.id, competition.event_id, artifact.user_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Insufficient permissions'
            )
        # Validate kind for competition artifact
        if data.kind and data.kind not in COMPETITION_ARTIFACT_KINDS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Invalid kind for competition artifact'
            )
    elif artifact.workout_id:
        workout = get_workout(db, artifact.workout_id)
        if not workout or workout.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Only workout owner can update artifacts'
            )
        # Validate kind for workout artifact
        if data.kind and data.kind not in WORKOUT_ARTIFACT_KINDS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Invalid kind for workout artifact'
            )

    updated = artifact_crud.update_artifact(
        db, artifact,
        tags=data.tags,
        kind=data.kind,
    )

    return ArtifactResponse(
        id=updated.id,
        competition_id=updated.competition_id,
        workout_id=updated.workout_id,
        user_id=updated.user_id,
        kind=updated.kind,
        file_path=updated.file_path,
        file_name=updated.file_name,
        file_size=updated.file_size,
        mime_type=updated.mime_type,
        tags=updated.tags,
        created_at=updated.created_at,
    )


# ===== 10.5 Delete Artifact =====

@artifact_router.delete('/api/artifacts/{artifact_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_artifact(
    artifact_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete artifact (hard delete)."""
    artifact = get_artifact_or_404(db, artifact_id)

    # Check permissions
    if artifact.competition_id:
        competition = get_competition(db, artifact.competition_id)
        if not competition or not artifact_crud.can_manage_competition_artifact(
            db, current_user.id, competition.event_id, artifact.user_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Insufficient permissions'
            )
    elif artifact.workout_id:
        workout = get_workout(db, artifact.workout_id)
        if not workout or workout.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Only workout owner can delete artifacts'
            )

    # Delete from MinIO
    delete_from_minio(artifact.file_path)

    # Delete record
    artifact_crud.delete_artifact(db, artifact)
    return None


# ===== 10.6 Download Artifact File =====

@artifact_router.get('/api/artifacts/{artifact_id}/download')
async def download_artifact(
    artifact_id: int,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Download artifact file (redirect to presigned URL)."""
    artifact = get_artifact_or_404(db, artifact_id)

    # Check visibility for workout artifacts
    if artifact.workout_id:
        workout = get_workout(db, artifact.workout_id)
        if workout and not artifact_crud.can_view_workout_artifact(
            db, current_user.id if current_user else None, workout.user_id, workout.privacy
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Private workout artifact'
            )

    # Redirect to presigned URL
    download_url = get_presigned_url(artifact.file_path)
    return RedirectResponse(url=download_url, status_code=status.HTTP_302_FOUND)


# ===== 10.7 Upload Workout Artifact =====

@artifact_router.post('/api/workouts/{workout_id}/artifacts', response_model=ArtifactResponse, status_code=status.HTTP_201_CREATED)
async def upload_workout_artifact(
    workout_id: int,
    file: Annotated[UploadFile, File()],
    kind: Annotated[ArtifactKind, Form()],
    tags: Annotated[str | None, Form()] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a workout artifact (owner only)."""
    workout = get_workout_or_404(db, workout_id)

    # Check ownership
    if workout.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only workout owner can upload artifacts'
        )

    # Validate artifact kind
    if kind not in WORKOUT_ARTIFACT_KINDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid kind for workout artifact. Allowed: {", ".join(k.value for k in WORKOUT_ARTIFACT_KINDS)}'
        )

    # Validate file
    extension, mime_type = validate_file(file, kind)
    validation = FILE_VALIDATION[kind]

    # Build file path
    file_path = f'users/{current_user.id}/workouts/{workout_id}/{kind.value}/{file.filename}'

    # Upload to MinIO
    file_size = await upload_to_minio(file, file_path, validation['max_size'])

    # Parse tags
    tags_list = [t.strip() for t in tags.split(',')] if tags else None

    # Create artifact record
    artifact = artifact_crud.create_artifact(
        db,
        user_id=current_user.id,
        kind=kind,
        file_path=file_path,
        file_name=file.filename,
        file_size=file_size,
        mime_type=mime_type,
        workout_id=workout_id,
        tags=tags_list,
    )

    return ArtifactResponse(
        id=artifact.id,
        competition_id=artifact.competition_id,
        workout_id=artifact.workout_id,
        user_id=artifact.user_id,
        kind=artifact.kind,
        file_path=artifact.file_path,
        file_name=artifact.file_name,
        file_size=artifact.file_size,
        mime_type=artifact.mime_type,
        tags=artifact.tags,
        created_at=artifact.created_at,
    )


# ===== 10.8 List Workout Artifacts =====

@artifact_router.get('/api/workouts/{workout_id}/artifacts', response_model=ArtifactsListResponse)
async def list_workout_artifacts(
    workout_id: int,
    kind: ArtifactKind | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """List workout artifacts (follows privacy)."""
    workout = get_workout_or_404(db, workout_id)

    # Check visibility
    if not artifact_crud.can_view_workout_artifact(
        db, current_user.id if current_user else None, workout.user_id, workout.privacy
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Private workout'
        )

    artifacts, total = artifact_crud.get_workout_artifacts(
        db, workout_id,
        kind=kind,
        limit=limit,
        offset=offset
    )

    # Get user info for each artifact
    from ..user.user_crud import get_user
    items = []
    for artifact in artifacts:
        user = get_user(db, artifact.user_id)
        if user:
            items.append(build_artifact_list_item(artifact, user))

    return ArtifactsListResponse(
        artifacts=items,
        total=total,
        limit=limit,
        offset=offset,
    )
