"""enable_rls_on_public_tables

Revision ID: 423b2164b299
Revises: f1a2b3c4d5e6
Create Date: 2026-08-05 08:43:40.199999

Enables Row-Level Security on every table in the public schema with zero
policies. With RLS enabled and no policies, every role except the table owner
(and roles with rolbypassrls) is denied all access by default. This closes the
PostgREST public API hole on Supabase: unauthenticated/anonymous requests that
bypass FastAPI's auth layer can no longer read, write, or delete rows.

The app's role (postgres) has rolbypassrls=true, so backend access through
FastAPI/SQLAlchemy is unaffected. Auth is enforced entirely in FastAPI, so no
Postgres-level policies are added by design.

alembic_version is included even though it holds no user data: it sits in the
public schema, so Supabase's security advisor would still flag it without RLS,
and enabling RLS on it is harmless because the app role bypasses RLS (migrations
keep working).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '423b2164b299'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PUBLIC_TABLES = [
    "alembic_version",
    "chunks",
    "conversations",
    "documents",
    "messages",
    "query_logs",
    "users",
]


def upgrade() -> None:
    """Enable RLS on every public-schema table. No policies: deny-all for
    every role that does not bypass RLS."""
    for table in PUBLIC_TABLES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;")


def downgrade() -> None:
    """Disable RLS on the same tables, restoring pre-migration behavior."""
    for table in PUBLIC_TABLES:
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY;")
