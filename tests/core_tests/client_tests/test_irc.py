def test_get_client():
    from cloudbot.clients import irc
    from cloudbot.clients.irc.client import IrcClient
    assert irc.get_client() is IrcClient


def test_get_client_type():
    from cloudbot.clients import irc
    assert irc.get_client_type() == "irc"


def test_permission_data_matcher():
    from cloudbot.event import Event
    from cloudbot.clients.irc.permissions import IrcPrefixMatcher
    matcher = IrcPrefixMatcher("*!*@test")

    assert matcher.match(Event(mask="user!thing@test"))


def test_permission_manager():
    from cloudbot.clients.irc.permissions import IrcPermissionManager
    from cloudbot.event import Event

    class TestClient:
        config = None

    test_client = TestClient()
    test_client.config = {
        'permissions': {
            'test': {
                'users': [
                    '*!*@test'
                ],
                'perms': [
                    'testperm'
                ]
            }
        }
    }
    manager = IrcPermissionManager(test_client)
    test_event = Event(mask='nick!user@test')
    assert manager.has_perm(test_event, 'testperm')
