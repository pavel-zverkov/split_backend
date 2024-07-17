class Environments:

    LOG_LEVEL: str = 'DEBUG'

    # postgres
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str

    # minio
    MINIO_HOST: str
    MINIO_PORT: str
    ACCESS_KEY: str
    SECRET_KEY: str
