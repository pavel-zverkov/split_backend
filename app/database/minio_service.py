import json
import uuid
from io import BytesIO
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error
from loguru import logger

from ..config import Config
from .minio_integration import get_minio_client


# Bucket names
BUCKET_AVATARS = 'avatars'
BUCKET_CLUB_LOGOS = 'club-logos'
BUCKET_EVENT_LOGOS = 'event-logos'
BUCKET_ARTIFACTS = 'artifacts'

ALL_BUCKETS = [BUCKET_AVATARS, BUCKET_CLUB_LOGOS, BUCKET_EVENT_LOGOS, BUCKET_ARTIFACTS]


PUBLIC_BUCKETS = {BUCKET_AVATARS}


def _public_read_policy(bucket: str) -> str:
    return json.dumps({
        'Version': '2012-10-17',
        'Statement': [{
            'Effect': 'Allow',
            'Principal': {'AWS': ['*']},
            'Action': ['s3:GetObject'],
            'Resource': [f'arn:aws:s3:::{bucket}/*'],
        }],
    })


def init_buckets() -> None:
    """Initialize all required buckets if they don't exist."""
    client = get_minio_client()

    for bucket in ALL_BUCKETS:
        try:
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
                logger.info(f'Created bucket: {bucket}')
            else:
                logger.debug(f'Bucket already exists: {bucket}')

            if bucket in PUBLIC_BUCKETS:
                client.set_bucket_policy(bucket, _public_read_policy(bucket))
                logger.info(f'Set public-read policy on bucket: {bucket}')
        except S3Error as e:
            logger.error(f'Failed to create bucket {bucket}: {e}')
            raise


def _get_base_url() -> str:
    """Get the base URL for MinIO objects."""
    return f'http://{Config.MINIO_HOST}:{Config.MINIO_PORT}'


def _upload_file(
    bucket: str,
    object_name: str,
    data: BinaryIO | bytes,
    content_type: str,
    length: int = -1
) -> str:
    """Upload a file to MinIO and return the URL."""
    client = get_minio_client()

    if isinstance(data, bytes):
        data = BytesIO(data)
        length = len(data.getvalue())

    try:
        client.put_object(
            bucket_name=bucket,
            object_name=object_name,
            data=data,
            length=length,
            content_type=content_type,
        )
        url = f'{_get_base_url()}/{bucket}/{object_name}'
        logger.info(f'Uploaded {object_name} to {bucket}')
        return url
    except S3Error as e:
        logger.error(f'Failed to upload {object_name}: {e}')
        raise


def _delete_file(bucket: str, object_name: str) -> bool:
    """Delete a file from MinIO."""
    client = get_minio_client()

    try:
        client.remove_object(bucket_name=bucket, object_name=object_name)
        logger.info(f'Deleted {object_name} from {bucket}')
        return True
    except S3Error as e:
        logger.error(f'Failed to delete {object_name}: {e}')
        return False


def _get_extension(content_type: str) -> str:
    """Get file extension from content type."""
    mapping = {
        'image/jpeg': 'jpg',
        'image/png': 'png',
        'image/webp': 'webp',
        'image/gif': 'gif',
    }
    return mapping.get(content_type, 'bin')


# === Avatar Functions ===

def upload_avatar(user_id: int, data: bytes, content_type: str) -> str:
    """Upload a new avatar with a unique name and return its URL."""
    ext = _get_extension(content_type)
    object_name = f'{user_id}/{uuid.uuid4().hex}.{ext}'
    return _upload_file(BUCKET_AVATARS, object_name, data, content_type)


def list_avatars(user_id: int) -> list[dict]:
    """List all avatars for a user, sorted by last_modified descending."""
    client = get_minio_client()
    objects = client.list_objects(BUCKET_AVATARS, prefix=f'{user_id}/', recursive=True)
    result = []
    for obj in objects:
        result.append({
            'object_name': obj.object_name,
            'url': f'{_get_base_url()}/{BUCKET_AVATARS}/{obj.object_name}',
            'last_modified': obj.last_modified,
            'size': obj.size,
        })
    result.sort(key=lambda x: x['last_modified'], reverse=True)
    return result


def activate_avatar(object_name: str) -> str:
    """Touch an avatar object (server-side copy to itself) to make it the most recent. Returns URL."""
    from minio.commonconfig import CopySource
    client = get_minio_client()
    client.copy_object(BUCKET_AVATARS, object_name, CopySource(BUCKET_AVATARS, object_name))
    return f'{_get_base_url()}/{BUCKET_AVATARS}/{object_name}'


def delete_avatar_object(object_name: str) -> bool:
    """Delete a specific avatar object by name."""
    return _delete_file(BUCKET_AVATARS, object_name)


def delete_avatar(user_id: int) -> None:
    """Delete all avatars for a user (used on account deletion)."""
    avatars = list_avatars(user_id)
    for avatar in avatars:
        _delete_file(BUCKET_AVATARS, avatar['object_name'])


# === Club Logo Functions ===

def upload_club_logo(club_id: int, data: bytes, content_type: str) -> str:
    """Upload club logo and return URL."""
    ext = _get_extension(content_type)
    object_name = f'{club_id}/logo.{ext}'
    return _upload_file(BUCKET_CLUB_LOGOS, object_name, data, content_type)


def delete_club_logo(club_id: int) -> bool:
    """Delete club logo. Tries common extensions."""
    client = get_minio_client()

    for ext in ['jpg', 'png', 'webp', 'gif']:
        object_name = f'{club_id}/logo.{ext}'
        try:
            client.stat_object(BUCKET_CLUB_LOGOS, object_name)
            return _delete_file(BUCKET_CLUB_LOGOS, object_name)
        except S3Error:
            continue

    logger.warning(f'No logo found for club {club_id}')
    return False


# === Event Logo Functions ===

def upload_event_logo(event_id: int, data: bytes, content_type: str) -> str:
    """Upload event logo and return URL."""
    ext = _get_extension(content_type)
    object_name = f'{event_id}/logo.{ext}'
    return _upload_file(BUCKET_EVENT_LOGOS, object_name, data, content_type)


def delete_event_logo(event_id: int) -> bool:
    """Delete event logo. Tries common extensions."""
    client = get_minio_client()

    for ext in ['jpg', 'png', 'webp', 'gif']:
        object_name = f'{event_id}/logo.{ext}'
        try:
            client.stat_object(BUCKET_EVENT_LOGOS, object_name)
            return _delete_file(BUCKET_EVENT_LOGOS, object_name)
        except S3Error:
            continue

    logger.warning(f'No logo found for event {event_id}')
    return False


# === Artifact Functions ===

def upload_artifact(
    event_id: int,
    competition_id: int,
    artifact_type: str,
    artifact_id: int,
    filename: str,
    data: bytes,
    content_type: str
) -> str:
    """Upload artifact (map or GPS file) and return URL."""
    object_name = f'events/{event_id}/competitions/{competition_id}/{artifact_type}/{artifact_id}_{filename}'
    return _upload_file(BUCKET_ARTIFACTS, object_name, data, content_type)


def upload_workout_gps(
    event_id: int,
    competition_id: int,
    user_id: int,
    workout_id: int,
    filename: str,
    data: bytes,
    content_type: str
) -> str:
    """Upload workout GPS file and return URL."""
    object_name = f'events/{event_id}/competitions/{competition_id}/gps/{user_id}/{workout_id}_{filename}'
    return _upload_file(BUCKET_ARTIFACTS, object_name, data, content_type)


def delete_artifact(object_path: str) -> bool:
    """Delete an artifact by its path."""
    return _delete_file(BUCKET_ARTIFACTS, object_path)
