"""add pcs_per_unit and widen stock_quantity to float

Revision ID: 4ac8b15982f4
Revises: 0ca83f13e68d
Create Date: 2026-10-23 19:24:28.977470

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4ac8b15982f4'
down_revision = '0ca83f13e68d'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('assets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('pcs_per_unit', sa.Float(), nullable=True))
        batch_op.alter_column('stock_quantity',
               existing_type=sa.INTEGER(),
               type_=sa.Float(),
               existing_nullable=True)


def downgrade():
    with op.batch_alter_table('assets', schema=None) as batch_op:
        batch_op.alter_column('stock_quantity',
               existing_type=sa.Float(),
               type_=sa.INTEGER(),
               existing_nullable=True)
        batch_op.drop_column('pcs_per_unit')
