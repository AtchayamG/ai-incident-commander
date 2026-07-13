"""Patch execution artifacts (M5)

Adds the patch_execution_artifacts table that persists the immutable record
of each isolated-workspace patch run: the consumed single-use approval, the
gateway engine with explicit simulated/live provenance, the captured unified
diff with per-file change counts, the full sandbox lifecycle event log, and
proof of workspace destruction and source-fixture immutability. Stored as a
JSON document with scalar columns for the safety-relevant queries.

Revision ID: a9c1e6f3b208
Revises: e8a4f7c2d901
Create Date: 2026-07-12 18:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a9c1e6f3b208'
down_revision: str | Sequence[str] | None = 'e8a4f7c2d901'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'patch_execution_artifacts',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('incident_id', sa.String(length=100), nullable=False),
        sa.Column('approval_id', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('engine_id', sa.String(length=200), nullable=False),
        sa.Column('simulated', sa.Boolean(), nullable=False),
        sa.Column('artifact_hash', sa.String(length=100), nullable=False),
        sa.Column('document', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id'], ),
        sa.ForeignKeyConstraint(['approval_id'], ['approval_requests.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_patch_execution_artifacts_incident_id'),
        'patch_execution_artifacts',
        ['incident_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_patch_execution_artifacts_approval_id'),
        'patch_execution_artifacts',
        ['approval_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_patch_execution_artifacts_approval_id'),
        table_name='patch_execution_artifacts',
    )
    op.drop_index(
        op.f('ix_patch_execution_artifacts_incident_id'),
        table_name='patch_execution_artifacts',
    )
    op.drop_table('patch_execution_artifacts')
