"""add asset_movement_batches table and AssetMovement.batch_id

Revision ID: 163b5916d83c
Revises: 53543ceb11e8
Create Date: 2026-09-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '163b5916d83c'
down_revision = '53543ceb11e8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'asset_movement_batches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('movement_no', sa.String(length=30), nullable=True),
        sa.Column('movement_date', sa.Date(), nullable=False),
        sa.Column('to_location', sa.String(length=100), nullable=True),
        sa.Column('to_department', sa.String(length=100), nullable=True),
        sa.Column('to_pic', sa.String(length=100), nullable=True),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('from_signer_name', sa.String(length=100), nullable=True),
        sa.Column('from_signer_position', sa.String(length=100), nullable=True),
        sa.Column('to_signer_name', sa.String(length=100), nullable=True),
        sa.Column('to_signer_position', sa.String(length=100), nullable=True),
        sa.Column('from_signature', sa.Text(), nullable=True),
        sa.Column('to_signature', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('movement_no', name='uq_asset_movement_batches_movement_no'),
    )
    op.create_index(
        op.f('ix_asset_movement_batches_movement_date'),
        'asset_movement_batches',
        ['movement_date'],
    )

    with op.batch_alter_table('asset_movements', schema=None) as batch_op:
        batch_op.add_column(sa.Column('batch_id', sa.Integer(), nullable=True))
        batch_op.drop_constraint('uq_asset_movements_movement_no', type_='unique')
        batch_op.create_index(
            batch_op.f('ix_asset_movements_batch_id'), ['batch_id'],
        )
        batch_op.create_foreign_key(
            'fk_asset_movements_batch_id',
            'asset_movement_batches',
            ['batch_id'],
            ['id'],
        )

    # Tabel asset_movements masih 0 baris saat migration ini dibuat, jadi
    # aman langsung dijadikan NOT NULL tanpa backfill.
    with op.batch_alter_table('asset_movements', schema=None) as batch_op:
        batch_op.alter_column('batch_id', existing_type=sa.Integer(), nullable=False)


def downgrade():
    with op.batch_alter_table('asset_movements', schema=None) as batch_op:
        batch_op.drop_constraint('fk_asset_movements_batch_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_asset_movements_batch_id'))
        batch_op.drop_column('batch_id')
        batch_op.create_unique_constraint('uq_asset_movements_movement_no', ['movement_no'])

    op.drop_index(
        op.f('ix_asset_movement_batches_movement_date'),
        table_name='asset_movement_batches',
    )
    op.drop_table('asset_movement_batches')
