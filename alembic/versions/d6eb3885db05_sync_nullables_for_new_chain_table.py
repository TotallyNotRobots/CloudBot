"""sync nullables for new chain table

Revision ID: d6eb3885db05
Revises: a1c96e5a186d
Create Date: 2026-11-20 23:06:56.477799

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence


# revision identifiers, used by Alembic.
revision: str = "d6eb3885db05"
down_revision: str | Sequence[str] | None = "a1c96e5a186d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("chain_commands_v2"):
        with op.batch_alter_table("chain_commands_v2") as batch:
            batch.alter_column(
                "allowed", existing_type=sa.BOOLEAN(), nullable=False
            )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("chain_commands_v2"):
        with op.batch_alter_table("chain_commands_v2") as batch:
            batch.alter_column(
                "allowed", existing_type=sa.BOOLEAN(), nullable=True
            )
