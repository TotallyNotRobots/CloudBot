"""Add connection to permissions tables

Revision ID: 60f88c7765e0
Revises:
Create Date: 2025-10-14 18:25:56.029663

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

from cloudbot.bot import bot_instance
from cloudbot.util.database import Session

if TYPE_CHECKING:
    from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "60f88c7765e0"
down_revision: str | Sequence[str] | None = "263108d18172"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table("group_member", "group_member_old")
    op.rename_table("group_perm", "group_perm_old")
    op.rename_table("perm_group", "perm_group_old")

    old_group_table = sa.table(
        "perm_group_old",
        sa.column("name", sa.String()),
        sa.column("config", sa.Boolean()),
    )
    group_table = op.create_table(
        "perm_group",
        sa.Column("connection", sa.String(), nullable=False, primary_key=True),
        sa.Column("name", sa.String(), nullable=False, primary_key=True),
        sa.Column("config", sa.Boolean()),
    )

    old_perm_table = sa.table(
        "group_perm_old",
        sa.column("group_id", sa.String()),
        sa.column("name", sa.String()),
        sa.column("config", sa.Boolean()),
    )
    perm_table = op.create_table(
        "group_perm",
        sa.Column("connection", sa.String(), nullable=False, primary_key=True),
        sa.Column("group_id", sa.String(), nullable=False, primary_key=True),
        sa.Column("name", sa.String(), nullable=False, primary_key=True),
        sa.Column("config", sa.Boolean()),
    )

    with op.batch_alter_table(perm_table.name) as batch:
        batch.create_foreign_key(
            "group_perm_group_fk",
            group_table.name,
            ["group_id", "connection"],
            ["name", "connection"],
        )

    old_member_table = sa.table(
        "group_member_old",
        sa.column("group_id", sa.String()),
        sa.column("mask", sa.String()),
        sa.column("config", sa.Boolean()),
    )
    member_table = op.create_table(
        "group_member",
        sa.Column("connection", sa.String(), nullable=False, primary_key=True),
        sa.Column("group_id", sa.String(), nullable=False, primary_key=True),
        sa.Column("mask", sa.String(), nullable=False, primary_key=True),
        sa.Column("config", sa.Boolean()),
    )

    with op.batch_alter_table(member_table.name) as batch:
        batch.create_foreign_key(
            "group_member_group_fk",
            group_table.name,
            ["group_id", "connection"],
            ["name", "connection"],
        )

    session = Session(bind=op.get_bind())
    op.bulk_insert(
        group_table,
        [
            {"connection": conn, "name": row.name, "config": row.config}
            for row in session.execute(sa.select(old_group_table)).all()
            for conn in bot_instance.get_or_raise()
            .get_connection_configs()
            .keys()
        ],
    )
    op.bulk_insert(
        perm_table,
        [
            {
                "connection": conn,
                "name": row.name,
                "group_id": row.group_id,
                "config": row.config,
            }
            for row in session.execute(sa.select(old_perm_table)).all()
            for conn in bot_instance.get_or_raise()
            .get_connection_configs()
            .keys()
        ],
    )
    op.bulk_insert(
        member_table,
        [
            {
                "connection": conn,
                "mask": row.mask,
                "group_id": row.group_id,
                "config": row.config,
            }
            for row in session.execute(sa.select(old_member_table)).all()
            for conn in bot_instance.get_or_raise()
            .get_connection_configs()
            .keys()
        ],
    )
    op.drop_table(old_perm_table.name)
    op.drop_table(old_member_table.name)
    op.drop_table(old_group_table.name)


def downgrade() -> None:
    """Downgrade schema."""
    op.rename_table("group_member", "group_member_old")
    op.rename_table("group_perm", "group_perm_old")
    op.rename_table("perm_group", "perm_group_old")

    old_group_table = sa.table(
        "perm_group_old",
        sa.column("connection", sa.String()),
        sa.column("name", sa.String()),
        sa.column("config", sa.Boolean()),
    )
    group_table = op.create_table(
        "perm_group",
        sa.Column("name", sa.String(), nullable=False, primary_key=True),
        sa.Column("config", sa.Boolean()),
    )

    old_perm_table = sa.table(
        "group_perm_old",
        sa.column("connection", sa.String()),
        sa.column("group_id", sa.String()),
        sa.column("name", sa.String()),
        sa.column("config", sa.Boolean()),
    )
    perm_table = op.create_table(
        "group_perm",
        sa.Column("group_id", sa.String(), nullable=False, primary_key=True),
        sa.Column("name", sa.String(), nullable=False, primary_key=True),
        sa.Column("config", sa.Boolean()),
    )

    with op.batch_alter_table(perm_table.name) as batch:
        batch.create_foreign_key(
            "group_perm_group_fk", group_table.name, ["group_id"], ["name"]
        )

    old_member_table = sa.table(
        "group_member_old",
        sa.column("connection", sa.String()),
        sa.column("group_id", sa.String()),
        sa.column("mask", sa.String()),
        sa.column("config", sa.Boolean()),
    )
    member_table = op.create_table(
        "group_member",
        sa.Column("group_id", sa.String(), nullable=False, primary_key=True),
        sa.Column("mask", sa.String(), nullable=False, primary_key=True),
        sa.Column("config", sa.Boolean()),
    )

    with op.batch_alter_table(member_table.name) as batch:
        batch.create_foreign_key(
            "group_member_group_fk", group_table.name, ["group_id"], ["name"]
        )

    session = Session(bind=op.get_bind())
    existing_groups = {}
    for group in session.execute(sa.select(old_group_table)).all():
        key = group.name
        if key not in existing_groups:
            existing_groups[key] = {"name": group.name, "config": group.config}

    existing_members = {}
    existing_perms = {}
    for member in session.execute(sa.select(old_member_table)).all():
        key = (member.group_id, member.mask)
        if key not in existing_members:
            existing_members[key] = {
                "mask": member.mask,
                "group_id": member.group_id,
                "config": member.config,
            }

    for perm in session.execute(sa.select(old_perm_table)).all():
        key = (perm.group_id, perm.name)
        if key not in existing_perms:
            existing_perms[key] = {
                "name": perm.name,
                "group_id": perm.group_id,
                "config": perm.config,
            }

    op.bulk_insert(group_table, [dict(row) for row in existing_groups.values()])
    op.bulk_insert(perm_table, [dict(row) for row in existing_perms.values()])
    op.bulk_insert(
        member_table, [dict(row) for row in existing_members.values()]
    )
    op.drop_table(old_perm_table.name)
    op.drop_table(old_member_table.name)
    op.drop_table(old_group_table.name)
