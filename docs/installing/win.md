### Getting Ready

We recommend that use you use a *unix system to run CloudBot in production, or Vagrant when developing CloudBot. However, it is possible to install natively on Windows.

First, make sure you have Python 3.6 or higher installed. It can be downloaded at [python.org](https://www.python.org/downloads/).

Next, you need to install `pip`.

You can usually install `pip` via the following python command in cmd:
```
python3 -m ensurepip
```

If that doesn't work, follow [this guide](https://simpledeveloper.com/how-to-install-easy_install/) and then run `easy_install pip` in cmd.

### Downloading

Download CloudBot from [https://github.com/TotallyNotRobots/CloudBot/archive/main.zip](https://github.com/TotallyNotRobots/CloudBot/archive/main.zip).

Unzip the resulting file, and continue to read this document.

### Installing Dependencies

Before you can run the bot, you need to install a few Python dependencies. All of CloudBot's dependencies are stored in the `requirements.txt` file.`

These can be installed with `pip` (The Python package manager) by running the following command in the bot directory:

    pip install -r requirements.txt

Because installing `lxml` can be quite difficult on Windows (you may get errors running the command above) due to it requiring compilation, you can find a pre-built distribution at [https://www.lfd.uci.edu/~gohlke/pythonlibs/#lxml](https://www.lfd.uci.edu/~gohlke/pythonlibs/#lxml)
