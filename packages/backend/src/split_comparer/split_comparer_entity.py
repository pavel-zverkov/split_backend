from datetime import datetime
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

        compare_result = \
            self.__create_analysis(
                split_left,
                split_right,
                common_ctrl_points
            )

        return compare_result

    def __compare_competition(
        self,
        competition_left: Competition,
        competition_right: Competition
    ) -> list[list[str]]:

        left_ctrl_points = competition_left.control_point_list
        right_ctrl_points = competition_right.control_point_list

        return find_common_subsequences(left_ctrl_points, right_ctrl_points)

    def __create_analysis(
        self,
        split_left: Split,
        split_right: Split,
        common_ctrl_points_block_list: list[list[str]]
    ) -> list[list[str]]:

        output = []
        for ctrl_points_block in common_ctrl_points_block_list:
            for ctrl_point in ctrl_points_block:

                ctrl_point_info_left = split_left.ctrl_points_info[ctrl_point]
                ctrl_point_info_right = split_right.ctrl_points_info[ctrl_point]

                left_time = ctrl_point_info_left.split_time
                right_time = ctrl_point_info_right.split_time
                diff = self.__get_str_diff(left_time, right_time)

                output.append(
                    [
                        ctrl_point,
                        left_time.strftime('%M:%S'),
                        right_time.strftime('%M:%S'),
                        diff
                    ]
                )

            output.append(['-', '', '', ''])

        output.append(
            [
                'Результат',
                split_left.ctrl_points_info['-1'].cumulative_time.strftime(
                    '%H:%M:%S'),
                split_right.ctrl_points_info['-1'].cumulative_time.strftime(
                    '%H:%M:%S'),
                self.__get_str_diff(
                    split_left.ctrl_points_info['-1'].cumulative_time,
                    split_right.ctrl_points_info['-1'].cumulative_time,
                )
            ]
        )

        return output

    def __get_str_diff(
        self,
        left_time: datetime,
        right_time: datetime
    ) -> str:

        diff = (left_time - right_time).total_seconds()
        sign = self.__get_sign(diff)

        return sign + datetime.fromtimestamp(abs(diff)).strftime('%M:%S')

    def __get_sign(self, seconds: float) -> str:
        if seconds > 0:
            return '+ '
        elif seconds < 0:
            return '- '
        return '= '
