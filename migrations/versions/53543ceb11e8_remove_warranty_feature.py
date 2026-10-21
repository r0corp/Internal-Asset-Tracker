"""remove warranty feature (warranty_histories table, assets.warranty column)

Revision ID: 53543ceb11e8
Revises: 1abfb7d36a86
Create Date: 2026-09-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '53543ceb11e8'
down_revision = '1abfb7d36a86'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table('warranty_histories')

    with op.batch_alter_table('assets', schema=None) as batch_op:
        batch_op.drop_column('warranty')


def downgrade():
    with op.batch_alter_table('assets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('warranty', sa.String(length=100), nullable=True))

    op.create_table(
        'warranty_histories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('old_warranty', sa.String(length=100), nullable=True),
        sa.Column('old_end_date', sa.Date(), nullable=True),
        sa.Column('new_warranty', sa.String(length=100), nullable=True),
        sa.Column('new_end_date', sa.Date(), nullable=True),
        sa.Column('changed_date', sa.Date(), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
