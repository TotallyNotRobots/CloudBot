# CloudBot
![Python application](https://github.com/TotallyNotRobots/CloudBot/workflows/Python%20application/badge.svg)
[![CodeFactor](https://www.codefactor.io/repository/github/totallynotrobots/cloudbot/badge/master)](https://www.codefactor.io/repository/github/totallynotrobots/cloudbot/overview/master)
[![codebeat badge](https://codebeat.co/badges/80316f30-26c0-44ec-b228-9158815d1995)](https://codebeat.co/projects/github-com-totallynotrobots-cloudbot-master)
[![codecov](https://codecov.io/gh/TotallyNotRobots/CloudBot/branch/master/graph/badge.svg)](https://codecov.io/gh/TotallyNotRobots/CloudBot)

CloudBot is a simple, fast, expandable open-source Python IRC Bot!

## Getting CloudBot

You have a few options for getting the bot, you can:
* Clone the `master` branch of this repository, using `git pull` to update
* Download the [latest source]
* Download the [latest release]

## Installing CloudBot

Firstly, CloudBot will only run on **Python 3.6 or higher**

To install CloudBot on *nix (linux, etc), see [here](docs/installing/nix.md)

To install CloudBot on Windows, see [here](docs/installing/win.md)


### Running CloudBot

Before you run the bot, rename `config.default.json` to `config.json` and edit it with your preferred settings. You can check if your JSON is valid using [jsonlint.com](http://jsonlint.com/)!

Once you have installed the required dependencies and renamed the config file, you can run the bot! Make sure you are in the correct folder and run the following command:

```
python3 -m cloudbot
```

## Getting help with CloudBot

### Documentation

The CloudBot documentation is currently somewhat outdated and may not be correct. If you need any help, please visit our [IRC channel](#support) and we will be happy to assist you.

To write your own plugins, visit the [Plugins Wiki Page](https://github.com/TotallyNotRobots/CloudBot/wiki/Writing-your-first-command-plugin).

More at the [Wiki Main Page](https://github.com/TotallyNotRobots/CloudBot/wiki).

### Support

The developers reside in [#gonzobot-dev](https://webchat.snoonet.org/#gonzobot-dev) on [Snoonet](https://snoonet.org) and would be glad to help you.

If you think you have found a bug/have a idea/suggestion, please **open a issue** here on Github and contact us on IRC!

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

## Changelog

See [CHANGELOG.md](CHANGELOG.md)

## License

CloudBot is **licensed** under the **GPL v3** license. The terms are as follows.

![GPL V3](https://www.gnu.org/graphics/gplv3-127x51.png)

    CloudBot

    Copyright © 2011-2015 Luke Rogers / CloudBot Project

    CloudBot is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    CloudBot is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with CloudBot.  If not, see <http://www.gnu.org/licenses/>.

This product includes GeoLite2 data created by MaxMind, available from
<a href="http://www.maxmind.com">http://www.maxmind.com</a>. GeoLite2 databases are distributed under the [Creative Commons Attribution-ShareAlike 3.0 Unported License](https://creativecommons.org/licenses/by-sa/3.0/)

![Powered by wordnik](https://www.wordnik.com/img/wordnik_badge_a1.png)

TV information is provided by [TheTVDB.com], but we are not endorsed or certified by [TheTVDB.com] or its affiliates.

Translations are Powered by [Yandex.Translate](https://translate.yandex.com)

This product uses data from <a href="http://wordnik.com">http://wordnik.com</a> in accordance with the wordnik.com API <a href="http://developer.wordnik.com/#!/terms">terms of service</a>.

[latest source]: https://github.com/TotallyNotRobots/CloudBot/archive/master.zip
[latest release]: https://github.com/TotallyNotRobots/CloudBot/releases/latest
[TheTVDB.com]: https://thetvdb.com/
