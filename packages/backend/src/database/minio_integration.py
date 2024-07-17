from minio import Minio
from loguru import logger

from ..config import Config


_minio_client = Minio(
    endpoint=f'{Config.MINIO_HOST}:{Config.MINIO_PORT}',
    access_key=Config.ACCESS_KEY,
    secret_key=Config.SECRET_KEY,
    secure=False
)

logger.success(f'Connected to minio {Config.MINIO_HOST}:{Config.MINIO_PORT}')


def get_minio_client() -> Minio:
    return _minio_client
