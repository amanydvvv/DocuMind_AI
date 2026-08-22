"""add_password_reset_tokens

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-08-22 02:30:00.000000

Creates the password_reset_tokens table used by the forgot-password flow.

Security notes:
- Only the SHA-256 hex digest of the raw token is stored (never plaintext).
- expires_at enforces a 30-minute window; tokens are rejected after expiry.
- used_at is set on first redemption; subsequent reuse of the same hash is rejected.
- ON DELETE CASCADE ensures tokens are purged when their parent user is deleted.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '3d4e5f6a7b8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
        ),
        # SHA-256 hex digest of the raw token — 64 hex chars.
        sa.Column('token_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_prt_user_id', 'password_reset_tokens', ['user_id'])
    op.create_index('idx_prt_token_hash', 'password_reset_tokens', ['token_hash'], unique=True)


def downgrade() -> None:
    op.drop_index('idx_prt_token_hash', table_name='password_reset_tokens')
    op.drop_index('idx_prt_user_id', table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
