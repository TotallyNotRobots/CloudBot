FROM mcr.microsoft.com/devcontainers/python:3.14@sha256:1af48f9bd555f7972b14424def113c166dab9c5027bd9d9f5cc57704a42974f2

RUN \
    pipx uninstall pydocstyle \
    && pipx uninstall pycodestyle \
    && pipx uninstall mypy \
    && pipx uninstall pylint \
    && pipx uninstall pytest \
    && pipx uninstall flake8 \
    && pipx uninstall black \
    && pipx uninstall autopep8 \
    && pipx uninstall bandit \
    && pipx uninstall pipenv \
    && pipx uninstall yapf \
    && pipx install commitizen \
    && umask 0002 \
    && mkdir -p "${PIPX_BIN_DIR}" \
    && chown -R "vscode:pipx" "${PIPX_HOME}" \
    && chmod -R g+r+w "${PIPX_HOME}"

ENV SHELL /bin/bash
