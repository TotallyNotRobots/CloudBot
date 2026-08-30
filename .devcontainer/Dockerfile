FROM mcr.microsoft.com/devcontainers/python:3.14@sha256:97152d71a6e42cc2f4f39d68fe72a94fc10baeb203700296dd3b2db4cfaaa686

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
