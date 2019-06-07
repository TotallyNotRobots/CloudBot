from plugins.core.optout import get_conn_optouts, optout_cache


def test_conn_case():
    l = optout_cache['TestConnection']

    assert get_conn_optouts('TestConnection') is l
    assert get_conn_optouts('testconnection') is l
    assert get_conn_optouts('testconnection1') is not l

    l = optout_cache['testconnection']

    assert get_conn_optouts('TestConnection') is l
    assert get_conn_optouts('testconnection') is l
    assert get_conn_optouts('testconnection1') is not l
