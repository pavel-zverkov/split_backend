from fastapi import (APIRouter,
                     Depends,
                     HTTPException)
from sqlalchemy.orm import Session

from ..database import get_db
from ..logger import logger
from . import competition_crud
from .competition_pydantic_model import Competition, CompetitionCreate

competition_router = APIRouter()


@competition_router.get(
    "/competition/",
    tags=["competitions"],
    response_model=Competition
)
async def read_competition(
    competition_name: str,
    sport_kind: str,
    db: Session = Depends(get_db)
) -> Competition | None:
    competition = competition_crud.get_competition_by_name(
        db, competition_name, sport_kind)
    return competition


@competition_router.post(
    "/competition/",
    tags=["competitions"],
    response_model=Competition
)
async def create_competition(
    competition: CompetitionCreate,
    db: Session = Depends(get_db)
) -> Competition | None:

    logger.debug(competition.__dict__)

    db_competition = competition_crud.get_competition_by_name(
        db, competition.name, competition.date, competition.sport_kind)
    if db_competition:
        raise HTTPException(
            status_code=400, detail=f"Competition {competition.name} already registered")
    return competition_crud.create_competition(db=db, competition=competition)
