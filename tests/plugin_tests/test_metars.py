from responses import RequestsMock


def test_metars():
    with RequestsMock() as reqs:
        reqs.add(
            reqs.GET, 'http://api.av-wx.com/metar/ABCD',
            json={
                'reports': [
                    {
                        'name': 'ABCD',
                        'raw_text': 'Foo Bar Test'
                    }
                ]
            }
        )
        from plugins.metars import metar
        assert metar('abcd') == 'ABCD: Foo Bar Test'


def test_taf():
    with RequestsMock() as reqs:
        reqs.add(
            reqs.GET, 'http://api.av-wx.com/taf/ABCD',
            json={
                'reports': [
                    {
                        'name': 'ABCD',
                        'raw_text': 'Foo Bar Test'
                    }
                ]
            }
        )
        from plugins.metars import taf
        assert taf('abcd') == 'ABCD: Foo Bar Test'

        assert taf('abc') == "please specify a valid station code see http://weather.rap.ucar.edu/surface/stations.txt for a list."
