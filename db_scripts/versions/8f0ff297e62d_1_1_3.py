"""1.1.3

Revision ID: 8f0ff297e62d
Revises: 4cccf1481cf7
Create Date: 2023-02-27 12:32:04.107371

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8f0ff297e62d'
down_revision = '4cccf1481cf7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    try:
        with op.batch_alter_table("SITE_BRUSH_TASK") as batch_op:
            batch_op.alter_column('DOWNLOAD_COUNT', type_=sa.Integer, existing_type=sa.Text)
            batch_op.alter_column('REMOVE_COUNT', type_=sa.Integer, existing_type=sa.Text)
            batch_op.alter_column('DOWNLOAD_SIZE', type_=sa.Integer, existing_type=sa.Text)
            batch_op.alter_column('UPLOAD_SIZE', type_=sa.Integer, existing_type=sa.Text)
    except Exception as e:
        print(str(e))
    # ### end Alembic commands ###


def downgrade() -> None:
    try:
        with op.batch_alter_table("SITE_BRUSH_TASK") as batch_op:
            batch_op.alter_column('DOWNLOAD_COUNT', type_=sa.Text, existing_type=sa.Integer)
            batch_op.alter_column('REMOVE_COUNT', type_=sa.Text, existing_type=sa.Integer)
            batch_op.alter_column('DOWNLOAD_SIZE', type_=sa.Text, existing_type=sa.Integer)
            batch_op.alter_column('UPLOAD_SIZE', type_=sa.Text, existing_type=sa.Integer)
    except Exception as e:
        print(str(e))
