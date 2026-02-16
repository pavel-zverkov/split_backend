"""add_claim_type_to_claim_requests

Revision ID: 43f405ac2152
Revises: 9c766d8bde84
Create Date: 2026-02-16 11:34:07.441841

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '43f405ac2152'
down_revision: Union[str, None] = '9c766d8bde84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    claimtype = sa.Enum('EVENT', 'CLUB', name='claimtype')
    claimtype.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'claim_requests',
        sa.Column('claim_type', claimtype, nullable=False, server_default='EVENT')
    )


def downgrade() -> None:
    op.drop_column('claim_requests', 'claim_type')
    sa.Enum('EVENT', 'CLUB', name='claimtype').drop(op.get_bind(), checkfirst=True)
