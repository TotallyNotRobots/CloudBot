# How to contribute
The following guidelines for contribution should be followed if you want to
submit a pull request.

## Basic Overview
1. Read [Github documentation](https://help.github.com/) and [Pull Request documentation](https://help.github.com/send-pull-requests/)
2. Fork the repository
3. Create a new branch with a descriptive name for your feature
4. Edit the files, add new files
5. Add tests for your changes or new feature
6. [Use pre-commit] to check that your changes follow the coding style
7. Add an entry in the [CHANGELOG]
8. Commit changes, push to your fork on GitHub
9. Create a new pull request, provide a short summary of changes in the title line, with more information in the description field.

## Use pre-commit
This project uses [pre-commit]
1. [Install pre-commit]
2. Run `pre-commit install` to add it as a git precommit hook to run checks on each `git commit` in the repository
3. Run `pre-commit run` before commiting, to check your changes easily

## Submit Changes
1. Push your changes to a topic branch in your fork of the repository.
2. Open a pull request to the original repository and choose the `main` branch.
3. Correct any issues shown by the automated checks
4. Join the [IRC channel] if you have any questions or concerns, or if you just want to talk with other devs

# Additional Resources
* [General GitHub documentation](https://help.github.com/)
* [GitHub pull request documentation](https://help.github.com/send-pull-requests/)
* [Read the Issue Guidelines by @necolas](https://github.com/necolas/issue-guidelines/blob/master/CONTRIBUTING.md) for more details
* [This CONTRIBUTING.md from here](https://github.com/anselmh/CONTRIBUTING.md)

[pre-commit]: https://pre-commit.com/
[Install pre-commit]: https://pre-commit.com/#install
[Use pre-commit]: #use-pre-commit
[CHANGELOG]: CHANGELOG.md
[IRC channel]: README.md#support
