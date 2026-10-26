"""add_distance_id_to_artifacts

Revision ID: a1b2c3d4e5f6
Revises: e4e13e588499
Create Date: 2026-04-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'e4e13e588499'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('artifacts', sa.Column('distance_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_artifacts_distance_id',
        'artifacts', 'distances',
        ['distance_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_artifacts_distance_id', 'artifacts', type_='foreignkey')
    op.drop_column('artifacts', 'distance_id')
