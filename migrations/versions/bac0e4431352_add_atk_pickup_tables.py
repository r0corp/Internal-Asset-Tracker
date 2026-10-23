"""add atk pickup tables

Revision ID: bac0e4431352
Revises: 8c6e27917aac
Create Date: 2026-10-23 17:47:52.960604

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bac0e4431352'
down_revision = '8c6e27917aac'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('atk_pickups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_name', sa.String(length=100), nullable=False),
        sa.Column('signature', sa.Text(), nullable=True),
        sa.Column('recorded_by', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('atk_pickup_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pickup_id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=True),
        sa.Column('asset_name', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('unit', sa.String(length=20), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ),
        sa.ForeignKeyConstraint(['pickup_id'], ['atk_pickups.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('atk_pickup_items', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_atk_pickup_items_asset_id'), ['asset_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_atk_pickup_items_pickup_id'), ['pickup_id'], unique=False)


def downgrade():
    with op.batch_alter_table('atk_pickup_items', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_atk_pickup_items_pickup_id'))
        batch_op.drop_index(batch_op.f('ix_atk_pickup_items_asset_id'))

    op.drop_table('atk_pickup_items')
    op.drop_table('atk_pickups')
