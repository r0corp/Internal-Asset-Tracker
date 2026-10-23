"""add scrap photos

Revision ID: 1cddbd023e2c
Revises: bac0e4431352
Create Date: 2026-10-23 18:05:49.604571

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1cddbd023e2c'
down_revision = 'bac0e4431352'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('scrap_photos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('scrap_record_id', sa.Integer(), nullable=True),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('label', sa.String(length=100), nullable=True),
        sa.Column('photo_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['scrap_record_id'], ['scrap_records.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('scrap_photos', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_scrap_photos_scrap_record_id'), ['scrap_record_id'], unique=False)


def downgrade():
    with op.batch_alter_table('scrap_photos', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_scrap_photos_scrap_record_id'))

    op.drop_table('scrap_photos')
