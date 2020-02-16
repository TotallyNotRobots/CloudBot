FROM python:3.7-slim

# install things:
# libenchant1c2a    pyenchant dependency
# libxml2-dev       python-lxml dependency
# libxslt-dev       python-lxml dependency
# zlib1g-dev        python-lxml dependency
RUN apt-get update && apt-get install -y --no-install-recommends \
    libenchant1c2a \
    libxml2-dev \
    libxslt-dev \
    zlib1g-dev \
    git \
    gcc \
&& rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

ENV APP_USER=gonzobot
RUN groupadd --gid=111 $APP_USER
RUN useradd --gid=111 --uid=111 --create-home $APP_USER

# set work directory
WORKDIR /home/$APP_USER
USER $APP_USER

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install pipenv
RUN pip install --user pipenv
ENV PATH="${PATH}:/home/${APP_USER}/.local/bin"

COPY --chown=111:111 Pipfile /home/$APP_USER
COPY --chown=111:111 Pipfile.lock /home/$APP_USER

# This is a dev version of the Dockerfile, so we also need the dev dependencies
RUN set -ex && /home/$APP_USER/.local/bin/pipenv install --pre --deploy --dev

COPY cloudbot /home/$APP_USER/cloudbot
COPY data /home/$APP_USER/data
COPY plugins  /home/$APP_USER/plugins

ENTRYPOINT ["pipenv", "run", "python", "-m", "cloudbot"]

## create link from project to ~/bot
#ln -sf /vagrant /home/vagrant/bot
#
## create start.sh script
#cat > /usr/local/bin/start-bot <<- _EOF_
#    #!/usr/bin/env bash
#    cd /home/vagrant/bot
#    python3 -m cloudbot
#_EOF_
#chmod +x /usr/local/bin/start-bot
