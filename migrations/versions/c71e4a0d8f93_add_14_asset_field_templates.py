"""add specification/stock_quantity/unit/selling_price and rename field_template values for 14-tab asset types

Revision ID: c71e4a0d8f93
Revises: b58d3f1a9c42
Create Date: 2026-10-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c71e4a0d8f93'
down_revision = 'b58d3f1a9c42'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('assets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('specification', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('stock_quantity', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('unit', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('selling_price', sa.Float(), nullable=True))

    # Perluas 3 field_template lama (lengkap/sederhana/kendaraan) jadi
    # skema baru 14 tab. "lengkap" -> "pc_laptop" (satu-satunya pemakainya
    # sejauh ini, Laptop, sudah pas masuk situ). "sederhana" -> "furniture"
    # (penamaan lebih jelas, perilaku sama). "kendaraan" tidak berubah.
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE categories SET field_template = 'pc_laptop' WHERE field_template = 'lengkap'"))
    bind.execute(sa.text("UPDATE categories SET field_template = 'furniture' WHERE field_template = 'sederhana'"))


def downgrade():
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE categories SET field_template = 'lengkap' WHERE field_template = 'pc_laptop'"))
    bind.execute(sa.text("UPDATE categories SET field_template = 'sederhana' WHERE field_template = 'furniture'"))

    with op.batch_alter_table('assets', schema=None) as batch_op:
        batch_op.drop_column('selling_price')
        batch_op.drop_column('unit')
        batch_op.drop_column('stock_quantity')
        batch_op.drop_column('specification')
