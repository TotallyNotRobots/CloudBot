from plugins.imdb import imdb_re


def test_imdb_re():
    def match(text):
        return imdb_re.match(text)

    assert not match('http://www.imdb.com/title/stuff')

    assert match('https://www.imdb.com/title/tt1950186/').group(1) == 'tt1950186'
    assert match('https://www.imdb.com/title/tt2575988/mediaviewer/rm668743424?ft0=name&fv0=nm1476909&ft1=image_type&fv1=still_frame').group(1) == 'tt2575988'
    assert match('http://www.imdb.com/title/tt1950186/').group(1) == 'tt1950186'
    assert match('http://www.imdb.com/title/tt2575988/mediaviewer/rm668743424?ft0=name&fv0=nm1476909&ft1=image_type&fv1=still_frame').group(1) == 'tt2575988'
    assert match('https://imdb.com/title/tt1950186/').group(1) == 'tt1950186'
    assert match('https://imdb.com/title/tt2575988/mediaviewer/rm668743424?ft0=name&fv0=nm1476909&ft1=image_type&fv1=still_frame').group(1) == 'tt2575988'
    assert match('http://imdb.com/title/tt1950186/').group(1) == 'tt1950186'
    assert match('http://imdb.com/title/tt2575988/mediaviewer/rm668743424?ft0=name&fv0=nm1476909&ft1=image_type&fv1=still_frame').group(1) == 'tt2575988'
    assert match('https://www.imdb.com/title/tt1950186').group(1) == 'tt1950186'
    assert match('http://www.imdb.com/title/tt1950186').group(1) == 'tt1950186'
    assert match('https://imdb.com/title/tt1950186').group(1) == 'tt1950186'
    assert match('http://imdb.com/title/tt1950186').group(1) == 'tt1950186'
