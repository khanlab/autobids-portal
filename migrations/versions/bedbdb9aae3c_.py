"""empty message

Revision ID: bedbdb9aae3c
Revises: ce257e328a3e
Create Date: 2021-07-26 13:43:18.015530

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bedbdb9aae3c'
down_revision = 'ce257e328a3e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('cfmm2tar', schema=None) as batch_op:
        batch_op.drop_constraint('fk_cfmm2tar_user_id_user', type_='foreignkey')
        batch_op.drop_column('user_id')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('cfmm2tar', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.INTEGER(), nullable=True))
        batch_op.create_foreign_key('fk_cfmm2tar_user_id_user', 'user', ['user_id'], ['id'])

    # ### end Alembic commands ###
