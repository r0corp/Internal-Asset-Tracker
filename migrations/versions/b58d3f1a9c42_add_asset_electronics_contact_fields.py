"""add office/personal email and phone number fields to assets

Revision ID: b58d3f1a9c42
Revises: a71c4e9f2b6d
Create Date: 2026-09-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b58d3f1a9c42'
down_revision = 'a71c4e9f2b6d'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('assets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('office_email', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('personal_email', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('phone_number', sa.String(length=30), nullable=True))


def downgrade():
    with op.batch_alter_table('assets', schema=None) as batch_op:
        batch_op.drop_column('phone_number')
        batch_op.drop_column('personal_email')
        batch_op.drop_column('office_email')
