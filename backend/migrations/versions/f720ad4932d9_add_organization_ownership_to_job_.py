"""add organization ownership to job descriptions

Revision ID: f720ad4932d9
Revises: ed7b2ba2ea0b
Create Date: 2026-11-24 23:13:54.332201

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f720ad4932d9'
down_revision: Union[str, Sequence[str], None] = 'ed7b2ba2ea0b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "job_descriptions",
        sa.Column("organization_id", sa.Integer(), nullable=True),
    )

    op.create_index(
        "ix_job_descriptions_organization_id",
        "job_descriptions",
        ["organization_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_job_descriptions_organization_id_organizations",
        "job_descriptions",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_job_descriptions_organization_id_organizations",
        "job_descriptions",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_job_descriptions_organization_id",
        table_name="job_descriptions",
    )

    op.drop_column(
        "job_descriptions",
        "organization_id",
    )
