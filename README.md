# CloudBot
![Python application](https://github.com/TotallyNotRobots/CloudBot/workflows/Python%20application/badge.svg)
[![CodeFactor](https://www.codefactor.io/repository/github/totallynotrobots/cloudbot/badge/gonzobot)](https://www.codefactor.io/repository/github/totallynotrobots/cloudbot/overview/gonzobot)
[![codebeat badge](https://codebeat.co/badges/3e5866e3-fe94-4c92-9dd7-8fbd616bc2ac)](https://codebeat.co/projects/github-com-totallynotrobots-cloudbot-gonzobot)
[![codecov](https://codecov.io/gh/TotallyNotRobots/CloudBot/branch/gonzobot/graph/badge.svg)](https://codecov.io/gh/TotallyNotRobots/CloudBot)

CloudBot is a simple, fast, expandable open-source Python IRC Bot!

## Getting CloudBot

There are currently four different branches of this repository, each with a different level of stability:
 - **gonzobot** *(stable)*: This branch contains everything in the **master** branch plus additional plugins added for Snoonet IRC. This branch is the currently maintained branch which will also contain many fixes for various bugs from the master branch.
 - **gonzobot-dev** *(unstable)*: This branch is based off of the **gonzobot** branch and includes new plugins that are not fully tested.
 - **master** *(stable (old))*: This branch contains stable, tested code. This branch is based directly on the upstream master branch and is not currently maintained.
 - **python3.4** *(unstable (old))*: This is the outdated testing branch from the upstream repo.

## Installing CloudBot

Firstly, CloudBot will only run on **Python 3.5.3 or higher**

To install CloudBot on *nix (linux, etc), see [here](docs/installing/nix.md)

To install CloudBot on Windows, see [here](docs/installing/win.md)


### Running CloudBot

Before you run the bot, rename `config.default.json` to `config.json` and edit it with your preferred settings. You can check if your JSON is valid using [jsonlint.com](http://jsonlint.com/)!

Once you have installed the required dependencies and renamed the config file, you can run the bot! Make sure you are in the correct folder and run the following command:

```
python3 -m cloudbot
```

Note that you can also run the `cloudbot/__main__.py` file directly, which will work from any directory.
```
python3 CloudBot/cloudbot/__main__.py
```
Specify the path as /path/to/repository/cloudbot/__main__.py, where `cloudbot` is inside the repository directory.

## Getting help with CloudBot

### Documentation

The CloudBot documentation is currently somewhat outdated and may not be correct. If you need any help, please visit our [IRC channel](https://webchat.snoonet.org/#gonzobot-dev) and we will be happy to assist you.

To write your own plugins, visit the [Plugins Wiki Page](https://github.com/CloudBotIRC/CloudBot/wiki/Writing-your-first-command-plugin).

More at the [Wiki Main Page](https://github.com/CloudBotIRC/CloudBot/wiki).

### Support

The developers reside in [#gonzobot-dev](https://webchat.snoonet.org/#gonzobot-dev) on [Snoonet](https://snoonet.org) and would be glad to help you.

If you think you have found a bug/have a idea/suggestion, please **open a issue** here on Github and contact us on IRC!

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

Translations are Powered by [Yandex.Translate](https://translate.yandex.com)

This product uses data from <a href="http://wordnik.com">http://wordnik.com</a> in accordance with the wordnik.com API <a href="http://developer.wordnik.com/#!/terms">terms of service</a>.
