import string


def test_make_pages():
    from cloudbot.util.pager import paginated_list
    pages = paginated_list([
        c * 50 for c in string.ascii_letters
    ], max_len=50)

    assert len(pages) == 26
