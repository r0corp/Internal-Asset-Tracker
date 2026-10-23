"""add vehicle fields and service records

Revision ID: eb2d4354895f
Revises: 1347fc05a95e
Create Date: 2026-10-23 11:22:20.355037

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'eb2d4354895f'
down_revision = '1347fc05a95e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('vehicle_service_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('service_date', sa.Date(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('recorded_by', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('vehicle_service_records', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_vehicle_service_records_asset_id'), ['asset_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_vehicle_service_records_service_date'), ['service_date'], unique=False)

    with op.batch_alter_table('assets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('warna', sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column('tahun_buat', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('masa_kir', sa.Date(), nullable=True))


def downgrade():
    with op.batch_alter_table('assets', schema=None) as batch_op:
        batch_op.drop_column('masa_kir')
        batch_op.drop_column('tahun_buat')
        batch_op.drop_column('warna')

    with op.batch_alter_table('vehicle_service_records', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_vehicle_service_records_service_date'))
        batch_op.drop_index(batch_op.f('ix_vehicle_service_records_asset_id'))

    op.drop_table('vehicle_service_records')
