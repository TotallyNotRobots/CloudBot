from responses import mock as resp_mock


class TestPaste:
    def test_hastebin(self):
        key = "aSdFvGs"
        from cloudbot.util.web import HASTEBIN_SERVER
        with resp_mock:
            resp_mock.add(
                resp_mock.POST,
                HASTEBIN_SERVER + '/documents',
                json={
                    "key": key
                }
            )
            from cloudbot.util import web
            assert web.paste("test", service='hastebin') == HASTEBIN_SERVER + '/' + key + '.txt'

    def test_ghostbin(self):
        key = "aSdFvGs"
        from cloudbot.util.web import SNOONET_PASTE
        with resp_mock:
            resp_mock.add(
                resp_mock.POST,
                SNOONET_PASTE + '/paste/new',
                status=301,
                adding_headers={"Location": SNOONET_PASTE + '/paste/' + key}
            )
            resp_mock.add(
                resp_mock.GET,
                SNOONET_PASTE + '/paste/' + key
            )
            from cloudbot.util import web
            assert web.paste("test", service='snoonet') == SNOONET_PASTE + '/paste/' + key
