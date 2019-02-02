class MockConn:
    def __init__(self, name, config):
        self.name = name
        self.config = config


def test_manager_load():
    import cloudbot.permissions
    from cloudbot.permissions import PermissionManager
    manager = PermissionManager(MockConn('testconn', {}))

    assert not manager.group_perms
    assert not manager.group_users
    assert not manager.perm_users
    assert not manager.get_groups()
    assert not manager.get_group_permissions('foobar')
    assert not manager.get_group_users('foobar')
    assert not manager.get_user_permissions('foo!bar@baz')
    assert not manager.get_user_groups('foo!bar@baz')
    assert not manager.group_exists('baz')
    assert not manager.user_in_group('foo!bar@baz', 'bing')

    cloudbot.permissions.backdoor = "*!user@host"

    assert manager.has_perm_mask("test!user@host", 'foo', False)
    assert not manager.has_perm_mask("test!otheruser@host", 'foo', False)

    user = 'user!a@host.com'
    user_mask = 'user!*@host??om'

    other_user = 'user1!b@hosaacom'
    other_user_mask = 'normaluser!*@*'

    cloudbot.permissions.backdoor = None
    manager = PermissionManager(MockConn('testconn', {
        'permissions': {
            'admins': {
                'users': [
                    user_mask
                ],
                'perms': [
                    'testperm'
                ]
            }
        }
    }))
    assert manager.group_exists('admins')
    assert manager.get_groups() == {'admins'}
    assert manager.get_user_groups(user) == ['admins']
    assert not manager.get_user_groups(other_user)
    assert manager.get_group_users('admins') == [user_mask]
    assert manager.get_group_permissions('admins') == ['testperm']
    assert manager.get_user_permissions(user) == {'testperm'}
    assert not manager.get_user_permissions(other_user)
    assert manager.has_perm_mask(user, 'testperm')
    assert manager.user_in_group(user, 'admins')

    assert manager.remove_group_user('admins', user) == [user_mask]
    manager.reload()

    assert 'admins' not in manager.get_user_groups(user)
    assert user_mask not in manager.get_group_users('admins')
    assert 'testperm' not in manager.get_user_permissions(user)
    assert not manager.has_perm_mask(user, 'testperm')
    assert not manager.user_in_group(user, 'admins')
