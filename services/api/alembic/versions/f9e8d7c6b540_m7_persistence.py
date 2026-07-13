"""Draft PR and communications persistence (M7)

Revision ID: f9e8d7c6b540
Revises: d4b8f1e6c530
Create Date: 2026-07-13 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'f9e8d7c6b540'
down_revision: str | Sequence[str] | None = 'd4b8f1e6c530'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create external_actions table
    op.create_table(
        'external_actions',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('incident_id', sa.String(length=100), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('provider', sa.String(length=100), nullable=False),
        sa.Column('idempotency_key', sa.String(length=200), nullable=False),
        sa.Column('approval_request_id', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('request_json', sa.JSON(), nullable=False),
        sa.Column('provider_receipt_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id']),
        sa.ForeignKeyConstraint(['approval_request_id'], ['approval_requests.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_external_actions_incident_id'),
        'external_actions',
        ['incident_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_external_actions_idempotency_key'),
        'external_actions',
        ['idempotency_key'],
        unique=True,
    )

    # Create postmortems table
    op.create_table(
        'postmortems',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('incident_id', sa.String(length=100), nullable=False),
        sa.Column('summary', sa.String(), nullable=False),
        sa.Column('impact', sa.String(), nullable=False),
        sa.Column('root_cause', sa.String(), nullable=False),
        sa.Column('resolution', sa.String(), nullable=False),
        sa.Column('timeline_json', sa.JSON(), nullable=False),
        sa.Column('action_items_json', sa.JSON(), nullable=False),
        sa.Column('markdown_content', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_postmortems_incident_id'),
        'postmortems',
        ['incident_id'],
        unique=True,
    )

    # Create communications table
    op.create_table(
        'communications',
        sa.Column('incident_id', sa.String(length=100), nullable=False),
        sa.Column('technical_update', sa.String(), nullable=False),
        sa.Column('stakeholder_update', sa.String(), nullable=False),
        sa.Column('resolution_note', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id']),
        sa.PrimaryKeyConstraint('incident_id'),
    )


def downgrade() -> None:
    op.drop_table('communications')
    op.drop_index(op.f('ix_postmortems_incident_id'), table_name='postmortems')
    op.drop_table('postmortems')
    op.drop_index(op.f('ix_external_actions_idempotency_key'), table_name='external_actions')
    op.drop_index(op.f('ix_external_actions_incident_id'), table_name='external_actions')
    op.drop_table('external_actions')
