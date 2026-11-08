"""voice agent tables

Revision ID: 7c1d94e2ab30
Revises: 3be2a94b50d0
Create Date: 2026-11-08 12:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c1d94e2ab30'
down_revision: Union[str, None] = '3be2a94b50d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('voice_agents',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('organization_id', sa.String(length=32), nullable=False),
    sa.Column('created_by', sa.String(length=32), nullable=True),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('language', sa.String(length=10), nullable=True),
    sa.Column('script', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_voice_agents_organization_id'), 'voice_agents', ['organization_id'], unique=False)
    op.create_table('voice_calls',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('agent_id', sa.String(length=32), nullable=False),
    sa.Column('organization_id', sa.String(length=32), nullable=False),
    sa.Column('to_phone', sa.String(length=32), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('provider', sa.String(length=30), nullable=True),
    sa.Column('provider_ref', sa.String(length=255), nullable=True),
    sa.Column('outcome_note', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['agent_id'], ['voice_agents.id'], ),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_voice_calls_organization_id'), 'voice_calls', ['organization_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_voice_calls_organization_id'), table_name='voice_calls')
    op.drop_table('voice_calls')
    op.drop_index(op.f('ix_voice_agents_organization_id'), table_name='voice_agents')
    op.drop_table('voice_agents')
