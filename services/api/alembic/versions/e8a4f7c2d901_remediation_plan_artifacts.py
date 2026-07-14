"""Remediation plan artifacts and approval bindings (M4)

Adds the remediation_plan_artifacts table that persists the bounded M4
remediation plan (files, steps, commands, budgets, risk, rollback) as a JSON
document with scalar version/hash/risk columns, and the approval_bindings
table that pins each APPLY_PATCH approval to one exact plan artifact
(id, version, content hash), approver role, and expiry.

Revision ID: e8a4f7c2d901
Revises: c3d5f1a9b024
Create Date: 2026-07-12 16:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e8a4f7c2d901'
down_revision: str | Sequence[str] | None = 'c3d5f1a9b024'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'remediation_plan_artifacts',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('incident_id', sa.String(length=100), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('artifact_hash', sa.String(length=100), nullable=False),
        sa.Column('risk_level', sa.String(length=50), nullable=False),
        sa.Column('document', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_remediation_plan_artifacts_incident_id'),
        'remediation_plan_artifacts',
        ['incident_id'],
        unique=False,
    )
    op.create_table(
        'approval_bindings',
        sa.Column('approval_id', sa.String(length=100), nullable=False),
        sa.Column('incident_id', sa.String(length=100), nullable=False),
        sa.Column('plan_id', sa.String(length=100), nullable=False),
        sa.Column('plan_version', sa.Integer(), nullable=False),
        sa.Column('plan_hash', sa.String(length=100), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('risk_level', sa.String(length=50), nullable=False),
        sa.Column('approver_role', sa.String(length=100), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['approval_id'], ['approval_requests.id'], ),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id'], ),
        sa.ForeignKeyConstraint(['plan_id'], ['remediation_plan_artifacts.id'], ),
        sa.PrimaryKeyConstraint('approval_id'),
    )
    op.create_index(
        op.f('ix_approval_bindings_incident_id'),
        'approval_bindings',
        ['incident_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_approval_bindings_incident_id'), table_name='approval_bindings')
    op.drop_table('approval_bindings')
    op.drop_index(
        op.f('ix_remediation_plan_artifacts_incident_id'),
        table_name='remediation_plan_artifacts',
    )
    op.drop_table('remediation_plan_artifacts')
