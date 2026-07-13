"""Investigation reports (M3)

Adds the investigation_reports table that persists the validated M3
investigation output for each incident run: status, the model gateway that
produced it, the remediation gate, and the full typed report document
(summary, ranked hypotheses, code mapping, unknowns, rejected claims).

Revision ID: c3d5f1a9b024
Revises: 7b91c4e2a6d5
Create Date: 2026-07-12 14:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c3d5f1a9b024'
down_revision: str | Sequence[str] | None = '7b91c4e2a6d5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'investigation_reports',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('incident_id', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('gateway', sa.String(length=100), nullable=False),
        sa.Column('remediation_enabled', sa.Boolean(), nullable=False),
        sa.Column('document', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_investigation_reports_incident_id'),
        'investigation_reports',
        ['incident_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_investigation_reports_incident_id'),
        table_name='investigation_reports',
    )
    op.drop_table('investigation_reports')
