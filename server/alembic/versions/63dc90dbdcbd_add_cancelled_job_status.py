"""add cancelled job status

Revision ID: 63dc90dbdcbd
Revises: 22692b64a3c2
Create Date: 2026-07-14 06:33:33.159354

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '63dc90dbdcbd'
down_revision: Union[str, Sequence[str], None] = '22692b64a3c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE job_status ADD VALUE IF NOT EXISTS 'CANCELLED'")
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
