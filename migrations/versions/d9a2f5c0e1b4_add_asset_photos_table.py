"""add asset_photos table for multiple photo upload per asset

Revision ID: d9a2f5c0e1b4
Revises: c71e4a0d8f93
Create Date: 2026-10-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd9a2f5c0e1b4'
down_revision = 'c71e4a0d8f93'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'asset_photos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('is_cover', sa.Boolean(), server_default=sa.text('0'), nullable=False),
        sa.Column('sort_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )

    with op.batch_alter_table('asset_photos', schema=None) as batch_op:
        batch_op.create_index('ix_asset_photos_asset_id', ['asset_id'], unique=False)

    # Pindahkan foto lama (kolom assets.photo, satu foto per asset) jadi
    # baris pertama di asset_photos supaya asset yang sudah punya foto
    # sebelum fitur multi-foto ada tetap tampil sebagai sampul.
    bind = op.get_bind()
    bind.execute(sa.text(
        """
        INSERT INTO asset_photos (asset_id, filename, is_cover, sort_order, created_at)
        SELECT id, photo, 1, 0, created_at FROM assets WHERE photo IS NOT NULL AND photo != ''
        """
    ))


def downgrade():
    with op.batch_alter_table('asset_photos', schema=None) as batch_op:
        batch_op.drop_index('ix_asset_photos_asset_id')

    op.drop_table('asset_photos')
