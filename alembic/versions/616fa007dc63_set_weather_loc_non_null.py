"""set weather.loc non-null

Revision ID: 616fa007dc63
Revises: d6eb3885db05
Create Date: 2026-11-20 23:30:40.412206

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

from plugins import weather

if TYPE_CHECKING:
    from collections.abc import Sequence


# revision identifiers, used by Alembic.
revision: str = "616fa007dc63"
down_revision: str | Sequence[str] | None = "d6eb3885db05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        sa.delete(weather.WeatherLocation).where(
            weather.WeatherLocation.loc.is_(None)
        )
    )
    with op.batch_alter_table("weather") as batch:
        batch.alter_column("loc", nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("weather") as batch:
        batch.alter_column("loc", nullable=True)
