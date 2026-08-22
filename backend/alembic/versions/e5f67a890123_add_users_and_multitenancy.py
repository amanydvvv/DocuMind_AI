"""add_users_and_multitenancy

Revision ID: e5f67a890123
Revises: c1a82f4e9012
Create Date: 2026-08-01 11:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'e5f67a890123'
down_revision: Union[str, None] = 'c1a82f4e9012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # 2. Add user_id column to documents, conversations, query_logs
    op.add_column('documents', sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_documents_user_id', 'documents', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_documents_user_id', 'documents', ['user_id'])

    # Drop old unique constraint on content_hash so multiple users can upload the same file
    op.drop_constraint('documents_content_hash_key', 'documents', type_='unique')

    op.add_column('conversations', sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_conversations_user_id', 'conversations', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_conversations_user_id', 'conversations', ['user_id'])

    op.add_column('query_logs', sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_query_logs_user_id', 'query_logs', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_query_logs_user_id', 'query_logs', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_query_logs_user_id', table_name='query_logs')
    op.drop_constraint('fk_query_logs_user_id', 'query_logs', type_='foreignkey')
    op.drop_column('query_logs', 'user_id')

    op.drop_index('ix_conversations_user_id', table_name='conversations')
    op.drop_constraint('fk_conversations_user_id', 'conversations', type_='foreignkey')
    op.drop_column('conversations', 'user_id')

    op.create_unique_constraint('documents_content_hash_key', 'documents', ['content_hash'])
    op.drop_index('ix_documents_user_id', table_name='documents')
    op.drop_constraint('fk_documents_user_id', 'documents', type_='foreignkey')
    op.drop_column('documents', 'user_id')

    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
