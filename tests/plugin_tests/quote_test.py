import pytest

from plugins import quote


@pytest.mark.parametrize(
    "q,n,n_quotes,out",
    [
        (("#foo", "foonick", ""), 1, 1, "[1/1] <f\u200boonick> "),
        (("", "", ""), 1, 1, "[1/1] <\u200b> "),
    ],
)
def test_format_quote(q, n, n_quotes, out):
    assert quote.format_quote(q, n, n_quotes) == out


def test_add_quote(mock_db, freeze_time):
    db = mock_db.session()
    mock_db.create_table(quote.qtable)
    res = quote.add_quote(db, "#chan", "foonick", "sender", "foo")
    assert res == "Quote added."
    assert mock_db.get_data(quote.qtable) == [
        ("#chan", "foonick", "sender", "foo", 1566497676.0, False)
    ]
