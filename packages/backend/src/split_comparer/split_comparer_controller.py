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
<!DOCTYPE html>
<html>
  <head>
    <title>Таблица</title>
    <link rel="stylesheet" type="text/css" href="/css/split_compare_style.css">
  </head>
  <body>
    <table>
      <tr>
        <th></th>
        <th>Значение 1</th>
        <th>Значение 2</th>
        <th></th>
      </tr>
      <tr>
        <td>Ячейка 1</td>
        <td>01:43</td>
        <td>03:01</td>
        <td>+1</td>
      </tr>
      <tr>
        <td>Ячейка 2</td>
        <td>02:14</td>
        <td>01:17</td>
        <td>-2</td>
      </tr>
      <tr>
        <td>Ячейка 2</td>
        <td>02:14</td>
        <td>02:14</td>
        <td>=</td>
      </tr>
    </table>

    <script src="/java_script/split_compare.js"></script> 
  </body>
</html>
    """
