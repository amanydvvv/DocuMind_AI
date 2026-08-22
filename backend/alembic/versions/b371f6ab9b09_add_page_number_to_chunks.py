"""add_page_number_to_chunks

Revision ID: b371f6ab9b09
Revises: cdde890276e6
Create Date: 2026-08-08 14:40:10.889835

Adds a dedicated nullable page_number column (1-based) to chunks so the
retrieval layer and SSE citation metadata can expose it to the frontend for
PDF highlighting without parsing JSONB. Nullable: markdown files and legacy
rows have no physical page mapping; their JSONB metadata (if present) is the
fallback source.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b371f6ab9b09'
down_revision: Union[str, None] = 'cdde890276e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable page_number column to chunks."""
    op.add_column("chunks", sa.Column("page_number", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Remove page_number column from chunks."""
    op.drop_column("chunks", "page_number")
