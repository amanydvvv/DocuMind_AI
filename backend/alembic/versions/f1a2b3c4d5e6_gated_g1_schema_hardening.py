"""gated_g1_schema_hardening

Revision ID: f1a2b3c4d5e6
Revises: e5f67a890123
Create Date: 2026-08-02 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e5f67a890123'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add is_active and is_verified to users
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('refresh_token_jti', sa.String(), nullable=True))

    # 2. Add composite index and check constraint to messages (idempotent if_not_exists)
    op.create_index('idx_messages_conv_created', 'messages', ['conversation_id', 'created_at'], if_not_exists=True)
    op.create_check_constraint('ck_messages_role', 'messages', "role IN ('user', 'assistant', 'system')")


def downgrade() -> None:
    op.drop_constraint('ck_messages_role', 'messages', type_='check')
    op.drop_index('idx_messages_conv_created', table_name='messages', if_exists=True)
    op.drop_column('users', 'refresh_token_jti')
    op.drop_column('users', 'is_verified')
    op.drop_column('users', 'is_active')
