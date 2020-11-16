[Quick Install](#quick-install)

## Quick Install
### Ubuntu (latest LTS)
To quickly get the bot up and running without much customization
1. [Install pipenv](https://github.com/pypa/pipenv#installation)
1. Run `git clone https://github.com/TotallyNotRobots/CloudBot.git`
1. `cd CloudBot`
1. `pipenv install --deploy`
1. Copy `config.default.json` to `config.json`, change settings as needed and validate it with [jsonlint](https://jsonlint.com/).
1. Run the bot while in the `CloudBot` directory
    1. `pipenv run bot`
