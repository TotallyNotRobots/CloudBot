"""sync nullables

Revision ID: 263108d18172
Revises:
Create Date: 2025-10-17 03:47:33.694639

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "263108d18172"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("channel_keys"):
        with op.batch_alter_table("channel_keys") as batch:
            batch.alter_column("key", existing_type=sa.VARCHAR(), nullable=True)

    if inspector.has_table("tell_messages"):
        with op.batch_alter_table("tell_messages") as batch:
            batch.alter_column(
                "conn", existing_type=sa.VARCHAR(), nullable=True
            )
            batch.alter_column(
                "sender", existing_type=sa.VARCHAR(), nullable=True
            )
            batch.alter_column(
                "target", existing_type=sa.VARCHAR(), nullable=True
            )
            batch.alter_column(
                "message", existing_type=sa.VARCHAR(), nullable=True
            )
            batch.alter_column(
                "is_read", existing_type=sa.BOOLEAN(), nullable=True
            )
            batch.alter_column(
                "time_sent", existing_type=sa.DATETIME(), nullable=True
            )
            batch.alter_column(
                "time_read", existing_type=sa.DATETIME(), nullable=True
            )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("tell_messages"):
        with op.batch_alter_table("tell_messages") as batch:
            batch.alter_column(
                "time_read", existing_type=sa.DATETIME(), nullable=False
            )
            batch.alter_column(
                "time_sent", existing_type=sa.DATETIME(), nullable=False
            )
            batch.alter_column(
                "is_read", existing_type=sa.BOOLEAN(), nullable=False
            )
            batch.alter_column(
                "message", existing_type=sa.VARCHAR(), nullable=False
            )
            batch.alter_column(
                "target", existing_type=sa.VARCHAR(), nullable=False
            )
            batch.alter_column(
                "sender", existing_type=sa.VARCHAR(), nullable=False
            )
            batch.alter_column(
                "conn", existing_type=sa.VARCHAR(), nullable=False
            )

    if inspector.has_table("channel_keys"):
        with op.batch_alter_table("channel_keys") as batch:
            batch.alter_column(
                "key", existing_type=sa.VARCHAR(), nullable=False
            )
