"""add category low stock threshold

Revision ID: 6eca45109207
Revises: 30e1f982da58
Create Date: 2026-10-22 15:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6eca45109207'
down_revision = '30e1f982da58'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.add_column(sa.Column('low_stock_threshold', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.drop_column('low_stock_threshold')
