from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from loguru import logger

from .auth.auth_controller import auth_router
from .competition.competition_contoller import competition_router
from .competition.distance_controller import distance_router
from .competition.registration_controller import registration_router
from .database import (Base,
                       engine,
                       tables)
from .event.event_controller import event_router
from .event.event_participation_controller import participation_router
from .event.total_config_controller import total_config_router
from .split_comparer.split_comparer_controller import split_comparer_router
from .user.user_controller import user_router
from .user.claim_request_controller import claim_request_router
from .user.follow_controller import follow_router
from .user.qualification_controller import qualification_router
from .workout.workout_controller import workout_router
from .workout.workout_split_controller import split_router
from .artifact.artifact_controller import artifact_router
from .result.result_controller import result_router
from .feed.feed_controller import feed_router
from .search.search_controller import search_router
from .club.club_controller import club_router
from .club.club_membership_controller import club_membership_router

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    try:
        from .database.minio_service import init_buckets
        init_buckets()
        logger.info('MinIO buckets initialized')
    except Exception as e:
        logger.warning(f'MinIO initialization failed: {e}. File uploads will not work.')

    yield
    # Shutdown (nothing to clean up)


app = FastAPI(title="Split App API", version="1.0.0", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(claim_request_router)
app.include_router(follow_router)
app.include_router(qualification_router)
app.include_router(workout_router)
app.include_router(split_router)
app.include_router(competition_router)
app.include_router(distance_router)
app.include_router(registration_router)
app.include_router(event_router)
app.include_router(participation_router)
app.include_router(total_config_router)
app.include_router(club_router)
app.include_router(club_membership_router)
app.include_router(split_comparer_router)
app.include_router(artifact_router)
app.include_router(result_router)
app.include_router(feed_router)
app.include_router(search_router)


@app.get("/")
async def root():
    return 'Hello! This is Split App API!'
