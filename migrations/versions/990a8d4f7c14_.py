"""empty message

Revision ID: 990a8d4f7c14
Revises: 384fe72e3812
Create Date: 2021-08-19 16:49:18.581601

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '990a8d4f7c14'
down_revision = '384fe72e3812'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('choices', sa.String(length=128), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('choices')

    # ### end Alembic commands ###
