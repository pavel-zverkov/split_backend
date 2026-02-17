"""add logo to events

Revision ID: c841346c4de4
Revises: 43f405ac2152
Create Date: 2026-02-16 22:22:55.608069

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c841346c4de4'
down_revision: Union[str, None] = '43f405ac2152'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('events', sa.Column('logo', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('events', 'logo')
