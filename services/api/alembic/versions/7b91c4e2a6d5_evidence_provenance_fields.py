"""Evidence provenance fields (M2)

Adds provider, content_hash, display_ref, redaction_rules, and captured_at to
evidence_items so every persisted evidence row carries full provenance:
which adapter captured it, when the underlying fact was observed, a hash of
the redacted content, a display reference, and the redaction rules applied.

Revision ID: 7b91c4e2a6d5
Revises: 114eaeeb8f04
Create Date: 2026-07-12 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7b91c4e2a6d5'
down_revision: str | Sequence[str] | None = '114eaeeb8f04'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Server defaults exist only so the ALTER succeeds on populated tables
# (SQLite requires a default for NOT NULL columns); the application always
# writes explicit values.
_EPOCH = '1970-01-01 00:00:00+00:00'


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('evidence_items') as batch:
        batch.add_column(
            sa.Column(
                'provider', sa.String(length=100), nullable=False, server_default='unknown'
            )
        )
        batch.add_column(
            sa.Column('content_hash', sa.String(length=100), nullable=False, server_default='')
        )
        batch.add_column(
            sa.Column('display_ref', sa.String(length=500), nullable=False, server_default='')
        )
        batch.add_column(
            sa.Column('redaction_rules', sa.JSON(), nullable=False, server_default='[]')
        )
        batch.add_column(
            sa.Column(
                'captured_at',
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=_EPOCH,
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('evidence_items') as batch:
        batch.drop_column('captured_at')
        batch.drop_column('redaction_rules')
        batch.drop_column('display_ref')
        batch.drop_column('content_hash')
        batch.drop_column('provider')
