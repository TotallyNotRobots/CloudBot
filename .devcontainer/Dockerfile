FROM mcr.microsoft.com/devcontainers/python:3.11@sha256:407616a78a9ec3bfbf736feedaf91d6c94e8cd0d2b90663da019c536e67e4ec4

RUN \
    pipx uninstall pydocstyle \
    && pipx uninstall pycodestyle \
    && pipx uninstall mypy \
    && pipx uninstall pylint \
    && pipx uninstall pytest \
    && pipx uninstall flake8 \
    && pipx uninstall black

RUN pipx install commitizen

RUN umask 0002 \
    && mkdir -p ${PIPX_BIN_DIR} \
    && chown -R "vscode:pipx" ${PIPX_HOME} \
    && chmod -R g+r+w "${PIPX_HOME}"

ENV SHELL /bin/bash
