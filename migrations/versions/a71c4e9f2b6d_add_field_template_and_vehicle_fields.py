"""add field_template to categories and plat_nomor/masa_pajak to assets

Revision ID: a71c4e9f2b6d
Revises: 163b5916d83c
Create Date: 2026-09-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a71c4e9f2b6d'
down_revision = '163b5916d83c'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.add_column(sa.Column('field_template', sa.String(length=20), server_default='lengkap', nullable=False))

    with op.batch_alter_table('assets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('plat_nomor', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('masa_pajak', sa.Date(), nullable=True))


def downgrade():
    with op.batch_alter_table('assets', schema=None) as batch_op:
        batch_op.drop_column('masa_pajak')
        batch_op.drop_column('plat_nomor')

    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.drop_column('field_template')
