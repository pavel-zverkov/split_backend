from fastapi import (APIRouter,
                     Depends,
                     HTTPException)
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..database import get_db

split_comparer_router = APIRouter()


@split_comparer_router.get(
    "/split_compare/",
    tags=['split'],
    response_class=HTMLResponse
)
async def compare_split():
    return """
    <html>
        <head>
            <title>Some HTML in here</title>
        </head>
        <body>
            <h1>Look ma! HTML!</h1>
        </body>
    </html>
    """
