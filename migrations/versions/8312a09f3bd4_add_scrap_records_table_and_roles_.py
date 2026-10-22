"""add scrap_records table and roles.allowed_categories

Revision ID: 8312a09f3bd4
Revises: d9a2f5c0e1b4
Create Date: 2026-10-22 09:07:50.092505

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8312a09f3bd4'
down_revision = 'd9a2f5c0e1b4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('scrap_records',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('scrap_type', sa.String(length=20), nullable=False),
    sa.Column('quantity', sa.Float(), nullable=False),
    sa.Column('unit', sa.String(length=10), nullable=False),
    sa.Column('recorded_date', sa.Date(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('scrap_records', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_scrap_records_recorded_date'), ['recorded_date'], unique=False)

    with op.batch_alter_table('roles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('allowed_categories', sa.Text(), nullable=True))

    # Tambah menu "Scrap" supaya langsung muncul di sidebar tanpa perlu
    # admin bikin manual lewat Menu Management - roles=NULL (tampil ke
    # semua role, sama seperti Dashboard/Asset; akses sesungguhnya tetap
    # digerbang oleh permission object "scrap" di route-nya).
    bind = op.get_bind()
    bind.execute(sa.text(
        """
        INSERT INTO menu_items (label, icon, url, "order", roles, is_active, is_divider, created_at)
        SELECT 'Scrap', 'bi-recycle', '/scrap', 40, NULL, 1, 0, CURRENT_TIMESTAMP
        WHERE NOT EXISTS (SELECT 1 FROM menu_items WHERE label = 'Scrap')
        """
    ))


def downgrade():
    bind = op.get_bind()
    bind.execute(sa.text(
        "DELETE FROM menu_items WHERE label = 'Scrap' AND url = '/scrap'"
    ))

    with op.batch_alter_table('roles', schema=None) as batch_op:
        batch_op.drop_column('allowed_categories')

    with op.batch_alter_table('scrap_records', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_scrap_records_recorded_date'))

    op.drop_table('scrap_records')
