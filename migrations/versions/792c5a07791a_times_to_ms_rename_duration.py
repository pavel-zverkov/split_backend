"""times_to_ms_rename_duration

All time columns are now stored in milliseconds.
- Rename workouts.duration_seconds -> workouts.duration_ms
- Multiply competition 10 result/split times by 1000 (they were stored in seconds)
- All other competitions already stored times in ms

Revision ID: 792c5a07791a
Revises: 9279ddd40bdf
Create Date: 2026-03-02 16:06:50.935916

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '792c5a07791a'
down_revision: Union[str, None] = '9279ddd40bdf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename workouts.duration_seconds -> duration_ms
    op.alter_column('workouts', 'duration_seconds', new_column_name='duration_ms')

    # Multiply competition 10 result times × 1000 (seconds → ms)
    op.execute("""
        UPDATE results
        SET
            time_total               = time_total * 1000,
            time_behind_leader       = CASE WHEN time_behind_leader IS NOT NULL
                                            THEN time_behind_leader * 1000 END,
            time_behind_distance_leader = CASE WHEN time_behind_distance_leader IS NOT NULL
                                               THEN time_behind_distance_leader * 1000 END
        WHERE competition_id = 10
    """)

    # Multiply competition 10 split times × 1000
    op.execute("""
        UPDATE result_splits
        SET
            cumulative_time = cumulative_time * 1000,
            split_time      = split_time * 1000
        WHERE result_id IN (
            SELECT id FROM results WHERE competition_id = 10
        )
    """)


def downgrade() -> None:
    op.alter_column('workouts', 'duration_ms', new_column_name='duration_seconds')

    op.execute("""
        UPDATE results
        SET
            time_total                  = time_total / 1000,
            time_behind_leader          = CASE WHEN time_behind_leader IS NOT NULL
                                               THEN time_behind_leader / 1000 END,
            time_behind_distance_leader = CASE WHEN time_behind_distance_leader IS NOT NULL
                                               THEN time_behind_distance_leader / 1000 END
        WHERE competition_id = 10
    """)

    op.execute("""
        UPDATE result_splits
        SET
            cumulative_time = cumulative_time / 1000,
            split_time      = split_time / 1000
        WHERE result_id IN (
            SELECT id FROM results WHERE competition_id = 10
        )
    """)
