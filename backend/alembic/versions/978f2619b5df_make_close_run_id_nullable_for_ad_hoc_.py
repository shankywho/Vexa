"""make_close_run_id_nullable_for_ad_hoc_reconciliation

Revision ID: 978f2619b5df
Revises: 761c0fe92564
Create Date: 2026-09-05 23:17:17.312077

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "978f2619b5df"
down_revision: Union[str, Sequence[str], None] = "761c0fe92564"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "reconciliation_results", "close_run_id", existing_type=sa.Uuid(), nullable=True
    )
    op.alter_column("exceptions", "close_run_id", existing_type=sa.Uuid(), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("exceptions", "close_run_id", existing_type=sa.Uuid(), nullable=False)
    op.alter_column(
        "reconciliation_results", "close_run_id", existing_type=sa.Uuid(), nullable=False
    )
