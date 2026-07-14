"""add result timestamps to jobs

Revision ID: 22692b64a3c2
Revises: fff3c554bc96
Create Date: 2026-07-14 05:04:29.523117

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '22692b64a3c2'
down_revision: Union[str, Sequence[str], None] = 'fff3c554bc96'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
    "jobs",
    sa.Column("result", sa.JSON(), nullable=True),
    )
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("jobs", "result")
    pass
