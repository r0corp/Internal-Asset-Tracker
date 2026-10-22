"""add category stock sequence

Revision ID: a1c7e4f9b2d3
Revises: 6eca45109207
Create Date: 2026-10-22 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1c7e4f9b2d3'
down_revision = '6eca45109207'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.add_column(sa.Column('stock_sequence', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.drop_column('stock_sequence')
