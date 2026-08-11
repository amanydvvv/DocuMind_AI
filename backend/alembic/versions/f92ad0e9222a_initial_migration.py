"""Initial migration

Revision ID: f92ad0e9222a
Revises: 
Create Date: 2026-07-31 05:44:57.256260

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'f92ad0e9222a'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Create documents table
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('content_hash', sa.String(), nullable=False, unique=True),
        sa.Column('file_type', sa.String(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 3. Create chunks table
    op.create_table(
        'chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('embedding', Vector(768), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_chunks_document', 'chunks', ['document_id'])

    # 4. Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 5. Create messages table
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('citations', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_messages_conversation', 'messages', ['conversation_id'])
    op.create_index('idx_messages_conv_created', 'messages', ['conversation_id', 'created_at'])

    # 6. Create query_logs table
    op.create_table(
        'query_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('retrieved_chunks', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('top_k', sa.Integer(), nullable=False),
        sa.Column('avg_similarity', sa.Float(), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_query_logs_created', 'query_logs', ['created_at'])


def downgrade() -> None:
    op.drop_table('query_logs')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('chunks')
    op.drop_table('documents')

