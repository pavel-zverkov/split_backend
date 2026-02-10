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

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = 'HS256'
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
