"""add category code column

Revision ID: 60debd2f830f
Revises: 8312a09f3bd4
Create Date: 2026-10-22 11:52:01.626341

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '60debd2f830f'
down_revision = '8312a09f3bd4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.add_column(sa.Column('code', sa.String(length=10), nullable=True))


def downgrade():
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.drop_column('code')
