from cloudbot.permissions import GroupBasedPermissionManager, EventDataMatcher


class IrcPrefixMatcher(EventDataMatcher):
    def match(self, event):
        return self.pattern == event.mask


class IrcPermissionManager(GroupBasedPermissionManager):
    def make_data_matcher(self, pattern):
        return IrcPrefixMatcher(pattern)
