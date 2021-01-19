### Downloading

[Quick Install](#quick-install)

#### Archive
Download CloudBot from [https://github.com/TotallyNotRobots/CloudBot/archive/main.zip](https://github.com/TotallyNotRobots/CloudBot/archive/main.zip) and unzip, or execute the following commands:
```bash
curl -Ls https://github.com/TotallyNotRobots/CloudBot/archive/main.zip > CloudBot.zip
unzip CloudBot.zip
cd CloudBot-main
```

#### Git

Alternately, you can also clone CloudBot by using:
```bash
git clone https://github.com/TotallyNotRobots/CloudBot.git
cd CloudBot
```

### Installing Dependencies

All of CloudBot's python dependencies are stored in the `requirements.txt` file, and can be installed with pip.

But first, you will need `git`, `python3-dev` and `libenchant1c2a`, `libxml2-dev`, `libxslt-dev` and `zlib1g-dev`. Install these with your system's package manager.

For example, on a Debian-based system, you could use:
```bash
[sudo] apt-get install -y python3-dev git libenchant-dev libxml2-dev libxslt-dev zlib1g-dev
```

You will also need to install `pip`, which can be done by following [this guide](https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/#installing-pip)

It is also recommended that you create a virtual environment for the bot to isolate it from system library updates. First, [install the venv package](https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/#installing-virtualenv) if required, and then [create the virtual environment](https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/#creating-a-virtual-environment)

We will refer to the virtual environment directory as `<VENV_DIR>` from here on.

Once the virtual environment is created, [activate it](https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/#activating-a-virtual-environment).

Finally, install the python dependencies using `pip` using the following command in the CloudBot directory:
```bash
pip install -Ur requirements.txt
```

Now you are ready to run the bot! This can be done simply by executing the cloudbot module like so
```bash
python -m cloudbot
```
or without activating the virtual environment, use
```bash
<VENV_DIR>/bin/python -m cloudbot
```

## Quick Install
### Ubuntu (latest LTS)
To quickly get the bot up and running without much customization
1. Run `git clone https://github.com/TotallyNotRobots/CloudBot.git`
1. `cd CloudBot`
1. `python3 -m venv venv --clear`
1. `venv/bin/python -m pip install -Ur requirements.txt`
1. Copy `config.default.json` to `config.json`, change settings as needed and validate it with [jsonlint](https://jsonlint.com/).
1. Run the bot while in the `CloudBot` directory
    1. `venv/bin/python -m cloudbot`
