import logging
from typing import Optional

from irclib.util.compare import match_mask
from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from cloudbot.util import database
from cloudbot.util.database import Session

logger = logging.getLogger("cloudbot")

# put your hostmask here for magic
# it's disabled by default, see has_perm_mask()
backdoor: Optional[str] = None


class Group(database.Base):
    __tablename__ = "perm_group"

    name = Column(String, nullable=False, primary_key=True)
    members = relationship("GroupMember", back_populates="group", uselist=True)
    perms = relationship(
        "GroupPermission", back_populates="group", uselist=True
    )

    config = Column(Boolean, default=False)

    def is_member(self, mask):
        for member in self.members:
            if match_mask(mask.lower(), member.mask):
                return True

        return False


class GroupMember(database.Base):
    __tablename__ = "group_member"

    group_id = Column(String, ForeignKey(Group.name), primary_key=True)
    group = relationship(Group, back_populates="members", uselist=False)

    mask = Column(String, primary_key=True, nullable=False)

    config = Column(Boolean, default=False)


class GroupPermission(database.Base):
    __tablename__ = "group_perm"

    group_id = Column(String, ForeignKey(Group.name), primary_key=True)
    group = relationship(Group, back_populates="perms", uselist=False)

    name = Column(String, primary_key=True, nullable=False)

    config = Column(Boolean, default=False)


class PermissionManager:
    def __init__(self, conn):
        logger.info(
            "[%s|permissions] Created permission manager for %s.",
            conn.name,
            conn.name,
        )

        self.name = conn.name
        self.config = conn.config

        session = Session()
        Group.__table__.create(session.bind, checkfirst=True)
        GroupPermission.__table__.create(session.bind, checkfirst=True)
        GroupMember.__table__.create(session.bind, checkfirst=True)

        self.reload()

    def reload(self):
        session = Session()

        updated = []
        for group_id, data in self.config.get("permissions", {}).items():
            group = self.get_group(group_id)
            if not group:
                group = Group(name=group_id)
                session.add(group)

            group.config = True
            updated.append(group)

            for user in data["users"]:
                member = session.get(
                    GroupMember, {"group_id": group_id, "mask": user}
                )
                if not member:
                    member = GroupMember(group_id=group_id, mask=user)
                    session.add(member)

                member.config = True
                updated.append(member)

            for perm in data["perms"]:
                binding = session.get(
                    GroupPermission, {"group_id": group_id, "name": perm}
                )
                if not binding:
                    binding = GroupPermission(group_id=group_id, name=perm)
                    session.add(binding)

                binding.config = True
                updated.append(binding)

        session.commit()

        for item in session.query(GroupMember).filter_by(config=True).all():
            if item not in updated:
                session.delete(item)

        for item in session.query(GroupPermission).filter_by(config=True).all():
            if item not in updated:
                session.delete(item)

        for item in session.query(Group).filter_by(config=True).all():
            if item not in updated:
                session.delete(item)

        session.commit()

    def has_perm_mask(self, user_mask, perm, notice=True):
        if backdoor and match_mask(user_mask.lower(), backdoor.lower()):
            return True

        for allowed_mask in self.get_perm_users(perm):
            if match_mask(user_mask.lower(), allowed_mask):
                if notice:
                    logger.info(
                        "[%s|permissions] Allowed user %s access to %s",
                        self.name,
                        user_mask,
                        perm,
                    )

                return True

        return False

    def get_perm_users(self, perm):
        session = Session()
        member_masks = (
            session.query(GroupMember.mask)
            .filter(
                GroupMember.group_id.in_(
                    session.query(GroupPermission.group_id).filter(
                        GroupPermission.name == perm
                    )
                )
            )
            .all()
        )

        return [item[0] for item in member_masks]

    def get_groups(self):
        return Session().query(Group).all()

    def get_group_permissions(self, name):
        group = self.get_group(name)
        if not group:
            return []

        return [perm.name for perm in group.perms]

    def get_group_users(self, name):
        group = self.get_group(name)
        if not group:
            return []

        return [member.mask for member in group.members]

    def get_user_permissions(self, user_mask):
        return {
            perm.name
            for group in self.get_user_groups(user_mask)
            for perm in group.perms
        }

    def get_user_groups(self, user_mask):
        return [
            group for group in self.get_groups() if group.is_member(user_mask)
        ]

    def get_group(self, group_id):
        return Session().get(Group, group_id)

    def group_exists(self, group):
        """
        Checks whether a group exists
        """
        return self.get_group(group) is not None

    def user_in_group(self, user_mask, group_id):
        """
        Checks whether a user is matched by any masks in a given group
        """
        group = self.get_group(group_id)
        if not group:
            return False

        return group.is_member(user_mask)

    def remove_group_user(self, group_id, user_mask):
        """
        Removes all users that match user_mask from group. Returns a list of user masks removed from the group.
        """
        group = self.get_group(group_id)
        if not group:
            return []

        masks_removed = []

        session = Session()
        for member in group.members:
            mask_to_check = member.mask
            if match_mask(user_mask.lower(), mask_to_check):
                masks_removed.append(mask_to_check)
                session.delete(member)

        Session().commit()

        return masks_removed

    def add_user_to_group(self, user_mask, group_id):
        """
        Adds user to group. Returns whether this actually did anything.
        """
        if self.user_in_group(user_mask, group_id):
            return False

        group = self.get_group(group_id)
        session = Session()
        if not group:
            group = Group(name=group_id)
            session.add(group)

        group.members.append(GroupMember(mask=user_mask))

        session.commit()

        return True
