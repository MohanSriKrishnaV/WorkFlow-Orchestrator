"""add next_attempt_at to outbox_events

Revision ID: fff3c554bc96
Revises: 7b9f91ca7cd3
Create Date: 2026-07-13 13:39:54.447156

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fff3c554bc96'
down_revision: Union[str, Sequence[str], None] = '7b9f91ca7cd3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
    "outbox_events",
    sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("outbox_events", "next_attempt_at")
    pass
