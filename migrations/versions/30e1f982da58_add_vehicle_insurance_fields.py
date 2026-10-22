"""add vehicle insurance fields

Revision ID: 30e1f982da58
Revises: 60debd2f830f
Create Date: 2026-10-22 12:35:35.921429

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '30e1f982da58'
down_revision = '60debd2f830f'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('assets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('asuransi', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('nomor_polis', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('masa_asuransi', sa.Date(), nullable=True))


def downgrade():
    with op.batch_alter_table('assets', schema=None) as batch_op:
        batch_op.drop_column('masa_asuransi')
        batch_op.drop_column('nomor_polis')
        batch_op.drop_column('asuransi')
