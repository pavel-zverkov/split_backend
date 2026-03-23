"""drop cp_code_unique constraint

Revision ID: 31cd266dd7b6
Revises: 792c5a07791a
Create Date: 2026-03-17 00:26:50.718642

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '31cd266dd7b6'
down_revision: Union[str, None] = '792c5a07791a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('cp_code_unique', 'control_points', type_='unique')


def downgrade() -> None:
    op.create_unique_constraint('cp_code_unique', 'control_points', ['distance_id', 'code'])
