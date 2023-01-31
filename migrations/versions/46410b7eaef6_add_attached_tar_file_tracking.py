"""Add attached tar file tracking

Revision ID: 46410b7eaef6
Revises: c4fdde0cd53d
Create Date: 2023-01-30 16:50:07.223370

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "46410b7eaef6"
down_revision = "c4fdde0cd53d"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("cfmm2tar_output", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("attached_tar_file", sa.Text(), nullable=True)
        )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("cfmm2tar_output", schema=None) as batch_op:
        batch_op.drop_column("attached_tar_file")

    # ### end Alembic commands ###
