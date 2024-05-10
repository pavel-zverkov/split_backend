from datetime import date, datetime
from typing import Any

from fastapi import (APIRouter,
                     Depends, HTTPException,
                     Request)
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.templating import _TemplateResponse

from ..competition.competition_crud import get_competition
from ..competition.competition_orm_model import Competition
from ..database import get_db
from ..event.event_crud import get_event
from ..event.event_orm_model import Event
from ..logger import logger
from ..split_comparer.split_control_point import ControlPoint
from ..user.user_crud import get_user
from ..user.user_orm_model import User
from ..workout.workout_crud import get_workout_by_event
from ..workout.workout_orm_model import Workout
from .split_comparer_entity import SplitComparerEntity
from .split_entity import Split

split_comparer_router = APIRouter()
template_list = Jinja2Templates(directory='frontend/html')


@split_comparer_router.get(
    "/split_compare/",
    tags=['split'],
    response_class=HTMLResponse
)
async def compare_split(
    request: Request,
    user_id_1: int,
    user_id_2: int,
    event_id: int,
    competition_date: date,
    db: Session = Depends(get_db)
) -> _TemplateResponse:

    event = _get_event(db, event_id)

    competitor_1 = _get_user(db, user_id_1)
    competitor_2 = _get_user(db, user_id_2)

    workout_1 = _get_workout_by_event(
        db, user_id_1, event_id, competition_date)
    workout_2 = _get_workout_by_event(
        db, user_id_2, event_id, competition_date)

    competition_1 = _get_competition(db, workout_1)
    competition_2 = _get_competition(db, workout_2)

    split_1 = __create_split(competitor_1, workout_1, competition_1)
    split_2 = __create_split(competitor_2, workout_2, competition_2)

    split_comparer = SplitComparerEntity()
    data = split_comparer.compare_splits(split_1, split_2)

    render = template_list.TemplateResponse(
        'split.html',
        {
            'request': request,
            'event': event.name,
            'description': competition_1.description,
            'date': competition_1.date,
            'competitor_1': split_1.person,
            'competitor_2': split_2.person,
            'data': data
        }
    )

    return render


def __create_split(
    user: User,
    workout: Workout,
    competition: Competition
) -> Split:

    person = user.first_name + ' ' + user.last_name
    class_code = ''  # TODO: Improve
    ctrl_points_info = __get_ctrl_points_info(workout.splits)
    # logger.debug(ctrl_points_info)
    result = ctrl_points_info['-1'].cumulative_time

    return Split(
        competition,
        person,
        class_code,
        ctrl_points_info,
        result
    )


def __get_ctrl_points_info(
    ctrl_points_info_dict: dict | Any
) -> dict[str, ControlPoint]:

    return {
        ctrl_point_info['id']: ControlPoint(
            ctrl_point_info['id'],
            datetime.strptime(
                ctrl_point_info['split_time'], '%H:%M:%S'),
            datetime.strptime(
                ctrl_point_info['cumulative_time'], '%H:%M:%S'),
            ctrl_point_info['place']
        )
        for ctrl_point_info in ctrl_points_info_dict.values()
    }


def _get_event(db: Session, event_id: int) -> Event:
    event = get_event(db, event_id)
    if not event:
        raise HTTPException(
            status_code=404, detail=f'Event with id={event_id} not found')

    return event


def _get_workout_by_event(
    db: Session,
    user_id: int,
    event_id: int,
    competition_date: date
) -> Workout:

    workout = get_workout_by_event(db, user_id, event_id, competition_date)
    if not workout:
        raise HTTPException(
            status_code=404,
            detail=f'Workout for user_id={user_id} and event_id={event_id} on date={competition_date} not found'
        )

    return workout


def _get_user(db: Session, user_id: int) -> User:
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=404, detail=f'User with id={user_id} not found')

    return user


def _get_competition(db: Session, workout: Workout) -> Competition:
    competition_id: int = workout.competition
    competition = get_competition(db, competition_id)
    if not competition:
        raise HTTPException(
            status_code=404,
            detail=f'Competition for user {workout.owner} on {workout.date} not found'
        )

    return competition
