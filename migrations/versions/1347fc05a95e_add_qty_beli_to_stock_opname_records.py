"""add qty_beli to stock_opname_records

Revision ID: 1347fc05a95e
Revises: b7d2a8e1f4c6
Create Date: 2026-10-23 11:11:44.495994

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1347fc05a95e'
down_revision = 'b7d2a8e1f4c6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('stock_opname_records', schema=None) as batch_op:
        batch_op.add_column(sa.Column('qty_beli', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('stock_opname_records', schema=None) as batch_op:
        batch_op.drop_column('qty_beli')
