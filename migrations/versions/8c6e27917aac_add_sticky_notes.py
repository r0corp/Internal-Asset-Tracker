"""add sticky notes

Revision ID: 8c6e27917aac
Revises: eb2d4354895f
Create Date: 2026-10-23 17:15:55.576324

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8c6e27917aac'
down_revision = 'eb2d4354895f'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('sticky_notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('color', sa.String(length=10), nullable=False),
        sa.Column('pinned', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('sticky_notes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_sticky_notes_user_id'), ['user_id'], unique=False)


def downgrade():
    with op.batch_alter_table('sticky_notes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_sticky_notes_user_id'))

    op.drop_table('sticky_notes')
