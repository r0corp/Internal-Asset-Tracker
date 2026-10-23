"""add scrap photo category

Revision ID: 0ca83f13e68d
Revises: 1cddbd023e2c
Create Date: 2026-10-23 18:13:23.978814

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0ca83f13e68d'
down_revision = '1cddbd023e2c'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('scrap_photos', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'category',
            sa.String(length=20),
            nullable=False,
            server_default='lainnya',
        ))


def downgrade():
    with op.batch_alter_table('scrap_photos', schema=None) as batch_op:
        batch_op.drop_column('category')
