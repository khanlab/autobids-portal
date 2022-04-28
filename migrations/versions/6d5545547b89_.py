"""empty message

Revision ID: 6d5545547b89
Revises: 511848007f2f
Create Date: 2022-04-28 10:23:04.502891

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6d5545547b89"
down_revision = "511848007f2f"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "datalad_dataset",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("study_id", sa.Integer(), nullable=False),
        sa.Column(
            "dataset_type",
            sa.Enum(
                "SOURCE_DATA", "RAW_DATA", "DERIVED_DATA", name="datasettype"
            ),
            nullable=False,
        ),
        sa.Column("ria_alias", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["study_id"],
            ["study.id"],
            name=op.f("fk_datalad_dataset_study_id_study"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_datalad_dataset")),
        sa.UniqueConstraint(
            "ria_alias", name=op.f("uq_datalad_dataset_ria_alias")
        ),
        sa.UniqueConstraint(
            "study_id",
            "dataset_type",
            name=op.f("uq_datalad_dataset_study_id"),
        ),
    )
    with op.batch_alter_table("study", schema=None) as batch_op:
        batch_op.drop_column("dataset_in_ria")
        batch_op.drop_column("tar_files_in_ria")

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("study", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "tar_files_in_ria",
                sa.BOOLEAN(),
                autoincrement=False,
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "dataset_in_ria",
                sa.BOOLEAN(),
                autoincrement=False,
                nullable=False,
            )
        )

    op.drop_table("datalad_dataset")
    # ### end Alembic commands ###
