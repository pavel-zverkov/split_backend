from fastapi import (APIRouter,
                     Depends,
                     HTTPException)
from sqlalchemy.orm import Session

from ..database import get_db
from ..user import user_crud
from ..user.user_pydantic_model import User, UserCreate

user_router = APIRouter()


@user_router.get("/user/", tags=["users"], response_model=User)
async def read_user(
    mobile_number: str,
    db: Session = Depends(get_db)
):
    user = user_crud.get_user(db=db, mobile_number=mobile_number)
    return user


@user_router.post("/user/", tags=["users"], response_model=User)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = user_crud.get_user(db, user.mobile_number)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return user_crud.create_user(db=db, user=user)
