"""users table

Revision ID: 35d2982f179f
Revises: 7a828f145fca
Create Date: 2021-05-04 16:11:24.498059

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '35d2982f179f'
down_revision = '7a828f145fca'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('answer',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('scanner', sa.String(length=20), nullable=True),
    sa.Column('scan_number', sa.Integer(), nullable=True),
    sa.Column('study_type', sa.String(length=20), nullable=True),
    sa.Column('familiarity', sa.String(length=20), nullable=True),
    sa.Column('principal', sa.String(length=20), nullable=True),
    sa.Column('project_name', sa.String(length=20), nullable=True),
    sa.Column('dataset_name', sa.String(length=20), nullable=True),
    sa.Column('retrospective_data', sa.String(length=20), nullable=True),
    sa.Column('retrospective_start', sa.Integer(), nullable=True),
    sa.Column('retrospective_end', sa.Integer(), nullable=True),
    sa.Column('consent', sa.String(length=20), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('comment',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('comment', sa.String(length=200), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('comment')
    op.drop_table('answer')
    # ### end Alembic commands ###
