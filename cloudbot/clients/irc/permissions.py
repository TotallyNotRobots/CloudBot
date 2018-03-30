import logging

from cloudbot.permissions import GroupBasedPermissionManager, EventDataMatcher

logger = logging.getLogger("cloudbot")


class IrcPrefixMatcher(EventDataMatcher):
    def match(self, event):
        return self.pattern == event.mask


class IrcPermissionManager(GroupBasedPermissionManager):
    def make_data_matcher(self, pattern):
        return IrcPrefixMatcher(pattern)
