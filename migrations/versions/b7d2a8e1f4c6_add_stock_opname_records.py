"""add stock opname records

Revision ID: b7d2a8e1f4c6
Revises: a1c7e4f9b2d3
Create Date: 2026-10-22 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7d2a8e1f4c6'
down_revision = 'a1c7e4f9b2d3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'stock_opname_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('period', sa.Date(), nullable=False),
        sa.Column('stok_awal', sa.Integer(), nullable=False),
        sa.Column('stok_keluar', sa.Integer(), nullable=False),
        sa.Column('stok_akhir', sa.Integer(), nullable=False),
        sa.Column('recorded_by', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asset_id', 'period', name='uq_stock_opname_asset_period'),
    )
    with op.batch_alter_table('stock_opname_records', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_stock_opname_records_asset_id'), ['asset_id'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_stock_opname_records_period'), ['period'], unique=False
        )


def downgrade():
    with op.batch_alter_table('stock_opname_records', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_stock_opname_records_period'))
        batch_op.drop_index(batch_op.f('ix_stock_opname_records_asset_id'))
    op.drop_table('stock_opname_records')
