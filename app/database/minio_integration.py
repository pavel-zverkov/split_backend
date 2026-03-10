from minio import Minio
from loguru import logger

from ..config import Config


_minio_client: Minio | None = None


def get_minio_client() -> Minio:
    """Get or create the MinIO client singleton."""
    global _minio_client

    if _minio_client is None:
        _minio_client = Minio(
            endpoint=f'{Config.MINIO_HOST}:{Config.MINIO_PORT}',
            access_key=Config.MINIO_ROOT_USER,
            secret_key=Config.MINIO_ROOT_PASSWORD,
            secure=False
        )
        logger.info(f'MinIO client configured for {Config.MINIO_HOST}:{Config.MINIO_PORT}')

    return _minio_client
