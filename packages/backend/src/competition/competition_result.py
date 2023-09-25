from datetime import datetime
from typing import NamedTuple
from sqlalchemy.orm import Session

from ..enums.enum_gender import Gender

from ..workout.workout_crud import get_competition_workouts
from ..user.user_crud import get_user
from ..competition.competition_crud import get_competition

DSQ = 'DSQ'


class ResultRow(NamedTuple):

    person: str
    competition_class: str
    result: datetime | str


class CompetitionResultCreator:

    @staticmethod
    def create_results(
            competition_id: int,
            db: Session
    ) -> list[ResultRow]:

        competition = get_competition(db, competition_id)
        workout_list = get_competition_workouts(db, competition_id)
        result_list = []
        for workout in workout_list:
            user = get_user(db, workout.user)
            person = user.last_name + user.first_name
            competition_class = get_competition_class(
                competition.class_list,
                user.gender,
                user.birthdate
            )

            result_info = workout.splits.get(-1)
            result = datetime.strptime(
                result_info['cumulative_time'],
                '%H:%M:%S'
            ) if result_info else DSQ

            result_list.append(
                ResultRow(
                    person=person,
                    competition_class=competition_class,
                    result=result
                )
            )

    def get_competition_class(
        class_list: list[str],
        gender: Gender,
        birth_year: datetime
    ) -> str:
        pass
