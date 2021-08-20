"""empty message

Revision ID: e125f6d12440
Revises: 2b0ce56b700c
Create Date: 2021-08-19 16:08:30.693282

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e125f6d12440'
down_revision = '2b0ce56b700c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('choices',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('desc', sa.String(length=200), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_choices'))
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('choices')
    # ### end Alembic commands ###
