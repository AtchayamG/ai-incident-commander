"""Verification run artifacts (M6)

Adds the verification_run_artifacts table that persists the immutable record
of each deterministic verification pass over a captured candidate patch: the
byte-exact diff reconstruction proof, every allowlisted subprocess check with
sanitized bounded output, the deterministic pass/fail, the failure
classification with base-state evidence, and the deterministic risk review.
Stored as a JSON document with scalar columns for the safety-relevant queries
(patch, pass/fail, failure classification).

Revision ID: d4b8f1e6c530
Revises: a9c1e6f3b208
Create Date: 2026-07-13 09:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd4b8f1e6c530'
down_revision: str | Sequence[str] | None = 'a9c1e6f3b208'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'verification_run_artifacts',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('incident_id', sa.String(length=100), nullable=False),
        sa.Column('patch_id', sa.String(length=100), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('failure_kind', sa.String(length=50), nullable=True),
        sa.Column('artifact_hash', sa.String(length=100), nullable=False),
        sa.Column('document', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id'], ),
        sa.ForeignKeyConstraint(['patch_id'], ['patch_attempts.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_verification_run_artifacts_incident_id'),
        'verification_run_artifacts',
        ['incident_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_verification_run_artifacts_patch_id'),
        'verification_run_artifacts',
        ['patch_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_verification_run_artifacts_patch_id'),
        table_name='verification_run_artifacts',
    )
    op.drop_index(
        op.f('ix_verification_run_artifacts_incident_id'),
        table_name='verification_run_artifacts',
    )
    op.drop_table('verification_run_artifacts')
