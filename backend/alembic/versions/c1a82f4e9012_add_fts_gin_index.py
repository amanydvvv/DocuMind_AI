

"""add_fts_gin_index

Revision ID: c1a82f4e9012
Revises: b7562f370bd8
Create Date: 2026-08-01 10:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c1a82f4e9012'
down_revision: Union[str, None] = 'b7562f370bd8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_chunks_fts ON chunks USING gin(to_tsvector('english', content));"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_chunks_fts;")
