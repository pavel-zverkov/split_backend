"""add_performance_indexes

Revision ID: e4e13e588499
Revises: 31cd266dd7b6
Create Date: 2026-03-21 07:53:13.546378

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4e13e588499'
down_revision: Union[str, None] = '31cd266dd7b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # results: filter + sort by distance
    op.create_index('ix_results_competition_distance', 'results', ['competition_id', 'distance_id'])
    # results: filter + sort by class
    op.create_index('ix_results_competition_class', 'results', ['competition_id', 'class'])
    # registrations: batch bib lookup by competition
    op.create_index('ix_registrations_competition_user', 'competition_registrations', ['competition_id', 'user_id'])
    # club memberships: batch club lookup per user
    op.create_index('ix_club_memberships_user_status', 'club_memberships', ['user_id', 'status'])
    # result_splits: batch load by result_id
    op.create_index('ix_result_splits_result_id', 'result_splits', ['result_id'])


def downgrade() -> None:
    op.drop_index('ix_results_competition_distance', table_name='results')
    op.drop_index('ix_results_competition_class', table_name='results')
    op.drop_index('ix_registrations_competition_user', table_name='competition_registrations')
    op.drop_index('ix_club_memberships_user_status', table_name='club_memberships')
    op.drop_index('ix_result_splits_result_id', table_name='result_splits')
