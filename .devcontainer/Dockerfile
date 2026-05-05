FROM mcr.microsoft.com/devcontainers/python:3.14@sha256:9e51c13505754efe79dd4a0b1a29523d3854090dabb8add3f3fa642ea3c98fad

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
