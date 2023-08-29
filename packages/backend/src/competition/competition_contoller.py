from fastapi import (APIRouter,
                     Depends,
                     HTTPException)
from sqlalchemy.orm import Session

from ..database import get_db
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
    db: Session = Depends(get_db)
):
    competition = competition_crud.get_competition(
        db, competition_name)
    return competition


@competition_router.post(
    "/competition/",
    tags=["competitions"],
    response_model=Competition
)
async def create_competition(competition: CompetitionCreate, db: Session = Depends(get_db)):
    return competition_crud.create_competition(db=db, competition=competition)
