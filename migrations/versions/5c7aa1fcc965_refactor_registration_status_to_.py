"""refactor registration status to competition level

Revision ID: 5c7aa1fcc965
Revises: c841346c4de4
Create Date: 2026-02-18 01:28:28.956977

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c7aa1fcc965'
down_revision: Union[str, None] = 'c841346c4de4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add new values to competitionstatus enum
    op.execute("ALTER TYPE competitionstatus ADD VALUE IF NOT EXISTS 'REGISTRATION_OPEN' AFTER 'PLANNED'")
    op.execute("ALTER TYPE competitionstatus ADD VALUE IF NOT EXISTS 'REGISTRATION_CLOSED' AFTER 'REGISTRATION_OPEN'")

    # 2. Migrate existing events with REGISTRATION_OPEN to PLANNED
    op.execute("UPDATE events SET status = 'PLANNED' WHERE status = 'REGISTRATION_OPEN'")

    # 3. Remove REGISTRATION_OPEN from eventstatus enum
    # PostgreSQL doesn't support DROP VALUE, so we recreate the type
    op.execute("ALTER TABLE events ALTER COLUMN status TYPE VARCHAR USING status::text")
    op.execute("DROP TYPE eventstatus")
    op.execute("CREATE TYPE eventstatus AS ENUM ('DRAFT', 'PLANNED', 'IN_PROGRESS', 'FINISHED', 'CANCELLED')")
    op.execute("ALTER TABLE events ALTER COLUMN status TYPE eventstatus USING status::eventstatus")


def downgrade() -> None:
    # 1. Add REGISTRATION_OPEN back to eventstatus
    op.execute("ALTER TABLE events ALTER COLUMN status TYPE VARCHAR USING status::text")
    op.execute("DROP TYPE eventstatus")
    op.execute("CREATE TYPE eventstatus AS ENUM ('DRAFT', 'PLANNED', 'REGISTRATION_OPEN', 'IN_PROGRESS', 'FINISHED', 'CANCELLED')")
    op.execute("ALTER TABLE events ALTER COLUMN status TYPE eventstatus USING status::eventstatus")

    # 2. Migrate competitions with new statuses back to PLANNED
    op.execute("UPDATE competitions SET status = 'PLANNED' WHERE status IN ('REGISTRATION_OPEN', 'REGISTRATION_CLOSED')")

    # 3. Remove new values from competitionstatus (recreate type)
    op.execute("ALTER TABLE competitions ALTER COLUMN status TYPE VARCHAR USING status::text")
    op.execute("DROP TYPE competitionstatus")
    op.execute("CREATE TYPE competitionstatus AS ENUM ('PLANNED', 'IN_PROGRESS', 'FINISHED', 'CANCELLED')")
    op.execute("ALTER TABLE competitions ALTER COLUMN status TYPE competitionstatus USING status::competitionstatus")
