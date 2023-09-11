from ..competition.competition_orm_model import Competition
from .split_entity import Split
from ..utils.common_list_item import find_common_subsequences


class SplitComparerEntity:

    def compare_splits(self, split_left: Split, split_right: Split) -> str:
        common_ctrl_points = \
            self.__compare_competition(
                split_left.competition,
                split_right.competition
            )

        compare_result_path = \
            self.__create_analysis(
                split_left,
                split_right,
                common_ctrl_points
            )

        return compare_result_path

    def __compare_competition(
        self,
        competition_left: Competition,
        competition_right: Competition
    ) -> list[str]:

        left_ctrl_points = competition_left.control_point_list
        right_ctrl_points = competition_right.control_point_list

        return find_common_subsequences(left_ctrl_points, right_ctrl_points)

    def __create_analysis(
        self,
        split_left: Split,
        split_right: Split,
        common_ctrl_points: list[str]
    ) -> str:
        pass
