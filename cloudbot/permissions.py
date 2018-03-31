from abc import ABC, abstractmethod
from collections import defaultdict

from polymatch import pattern_registry


class AbstractPermissionManager(ABC):
    def __init__(self, client):
        """
        :type client: .client.Client
        """
        self.client = client

        self.reload()

    @abstractmethod
    def has_perm(self, event, perm):
        """
        :type event: cloudbot.event.Event
        :type perm: str
        :rtype: bool
        """
        raise NotImplementedError

    @abstractmethod
    def reload(self):
        raise NotImplementedError


class EventDataMatcher(ABC):
    def __init__(self, pattern):
        """
        :type pattern: str
        """
        # If no pattern type is set, fall back to case-folded glob for compatibility
        if ':' not in pattern:
            pattern = 'glob:cf:' + pattern

        self._pattern = pattern_registry.pattern_from_string(pattern)
        self._pattern.compile()

    @property
    def pattern(self):
        return self._pattern

    @abstractmethod
    def match(self, event):
        """
        :type event: cloudbot.event.Event
        :rtype: bool
        """
        raise NotImplementedError


class NickMatcher(EventDataMatcher):
    def match(self, event):
        return self._pattern == event


class PermissionGroup:
    def __init__(self):
        self._permissions = set()
        self._matches = []

    @property
    def permissions(self):
        return self._permissions.copy()

    @permissions.setter
    def permissions(self, value):
        self._permissions.update(value)

    @property
    def patterns(self):
        return self._matches

    def add_match(self, match):
        """
        :type match: EventDataMatcher
        """
        self._matches.append(match)

    def add_perm(self, perm):
        """
        :type perm: str
        """
        self._permissions.add(perm)

    def has_perm(self, perm):
        """
        :type perm: str
        """
        return perm in self._permissions

    def is_member(self, event):
        return any(match.match(event) for match in self._matches)


class GroupBasedPermissionManager(AbstractPermissionManager):
    def __init__(self, client):
        """
        :type client: cloudbot.client.Client
        """

        self._groups = {}
        self._perms_to_groups = defaultdict(set)
        self._perms_to_users = defaultdict(set)

        super().__init__(client)

    def clear(self):
        self._groups.clear()
        self._perms_to_users.clear()
        self._perms_to_groups.clear()

    def make_group(self, name):
        """
        :type name: str
        :rtype: PermissionGroup
        """
        self._groups[name] = group = PermissionGroup()
        return group

    def get_group(self, name):
        """
        :type name: str
        :rtype: PermissionGroup
        """
        try:
            return self._groups[name]
        except LookupError:
            return self.make_group(name)

    def get_groups(self):
        return self._groups.copy()

    def get_group_names(self):
        return set(self._groups.keys())

    def get_group_permissions(self, group):
        """
        :type group: str | PermissionGroup
        :rtype: set(str)
        """
        if isinstance(group, str):
            group = self.get_group(group)

        return group.permissions

    def get_group_users(self, group):
        """
        :type group: str | PermissionGroup
        """
        if isinstance(group, str):
            group = self.get_group(group)

        return group.patterns

    def get_user_permissions(self, event):
        """
        :type event: cloudbot.event.Event
        :rtype: list[str]
        """
        permissions = set()
        for group in self._groups.values():
            if group.is_member(event):
                permissions.update(group.permissions)

        return permissions

    def get_user_groups(self, event):
        """
        :type event: cloudbot.event.Event
        :rtype: list[PermissionGroup]
        """
        return [group for group in self._groups if group.is_member(event)]

    def group_exists(self, name):
        """
        Checks whether a group exists
        :type name: str
        :rtype: bool
        """
        return name in self._groups

    def user_in_group(self, event, group):
        """
        :type event: cloudbot.event.Event
        :type group: str | PermissionGroup
        :rtype: bool
        """
        if isinstance(group, str):
            group = self.get_group(group)

        return group.is_member(event)

    def add_pattern_to_group(self, group, pattern):
        """
        :type group: str | PermissionGroup
        :type pattern: str
        """
        if isinstance(group, str):
            group = self.get_group(group)

        matcher = self.make_data_matcher(pattern)
        group.add_match(matcher)
        for perm in group.permissions:
            self._perms_to_users[perm].update(group.patterns)

    def add_perm_to_group(self, name, perm):
        """
        :type name: str
        :type perm: str
        """
        group = self.get_group(name)
        group.add_perm(perm)
        self._perms_to_groups[perm].add(group)
        self._perms_to_users[perm].update(group.patterns)

    def has_perm(self, event, perm):
        """
        :type event: cloudbot.event.Event
        :type perm: str
        :rtype: bool
        """
        for group in self._groups.values():  # type: PermissionGroup
            if perm in group.permissions and group.is_member(event):
                return True

        return False

    @abstractmethod
    def make_data_matcher(self, pattern):
        """
        :type pattern: str
        :rtype: EventDataMatcher
        """
        raise NotImplementedError

    def reload(self):
        self.clear()
        conf = self.client.config['permissions']
        for name, group_data in conf.items():
            group = self.get_group(name)
            group.permissions = _get_keys_opt(group_data, 'perms', 'permissions')
            for pattern in _get_keys_opt(group_data, 'users', 'masks', 'patterns'):
                self.add_pattern_to_group(group, pattern)


def _get_keys_opt(mapping, *keys):
    """
    :type mapping: collections.Mapping
    :type keys: tuple(any)
    """
    if not keys:
        raise TypeError("At least one key option must be provided")

    for key in keys:
        try:
            return mapping[key]
        except LookupError:
            pass

    raise KeyError(keys[0])


class NickBasedPermissionManager(GroupBasedPermissionManager):
    def make_data_matcher(self, pattern):
        return NickMatcher(pattern)
