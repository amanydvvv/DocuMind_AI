"""add_context_summary_to_conversations

Revision ID: cdde890276e6
Revises: 423b2164b299
Create Date: 2026-08-07 21:36:42.746536

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cdde890276e6'
down_revision: Union[str, None] = '423b2164b299'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'conversations',
        sa.Column('context_summary', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('conversations', 'context_summary')
