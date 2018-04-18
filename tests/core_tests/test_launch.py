from contextlib import redirect_stdout
from io import StringIO
from unittest import mock

import pytest

configs = [
    {
        "logging": {
            "console_debug": True,
            "file_debug": False,
            "show_plugin_loading": False,
            "show_motd": False,
            "show_server_info": False,
            "raw_file_log": False,
            "file_log": False
        }
    },
    {
        "logging": {
            "console_debug": False,
            "file_debug": False,
            "show_plugin_loading": False,
            "show_motd": False,
            "show_server_info": False,
            "raw_file_log": False,
            "file_log": False
        }
    }
]


def _get_output_for_config(config):
    if config["logging"]["console_debug"]:
        return [
            "[INFO] Starting CloudBot.",
            "[DEBUG] Stopping logging engine",
        ]

    return [
        "[INFO] Starting CloudBot."
    ]


@pytest.mark.parametrize("config_data,output", [
    (config, _get_output_for_config(config)) for config in configs
])
def test_basic_run(config_data, output):
    count = 0

    def _run_mock(self, *args, **kwargs):
        nonlocal count
        count += 1
        return False

    def _mock_reload_config(self, *args, **kwargs):
        self.update(config_data)

    with mock.patch('cloudbot.bot.CloudBot.__init__', lambda *args, **kwargs: None), \
         mock.patch('cloudbot.bot.CloudBot.run', _run_mock), \
         mock.patch('cloudbot.config.Config.load_config', _mock_reload_config), \
         redirect_stdout(StringIO()) as s:
        from cloudbot.__main__ import main
        main()
        assert count == 1
        lines = s.getvalue().splitlines()
        lines = [line.split(None, 1)[1] for line in lines]
        assert lines == output


class AppRestart(SystemExit):
    pass


def test_restart():
    def _mock_os_execv(*args, **kwargs):
        raise AppRestart()

    with mock.patch('cloudbot.bot.CloudBot.__init__', lambda *args, **kwargs: None), \
         mock.patch('cloudbot.bot.CloudBot.run', lambda *args, **kwargs: True), \
         mock.patch('cloudbot.config.Config.load_config', lambda *args, **kwargs: None), \
         mock.patch('os.execv', _mock_os_execv), \
         redirect_stdout(StringIO()):
        from cloudbot.__main__ import main
        with pytest.raises(AppRestart):
            main()
