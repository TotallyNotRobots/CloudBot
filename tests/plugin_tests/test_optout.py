from plugins.core.optout import get_conn_optouts, optout_cache


def test_conn_case():
    conn_list = optout_cache['TestConnection']

    assert get_conn_optouts('TestConnection') is conn_list
    assert get_conn_optouts('testconnection') is conn_list
    assert get_conn_optouts('testconnection1') is not conn_list

    conn_list = optout_cache['testconnection']

    assert get_conn_optouts('TestConnection') is conn_list
    assert get_conn_optouts('testconnection') is conn_list
    assert get_conn_optouts('testconnection1') is not conn_list
