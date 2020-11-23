#!/usr/bin/env bash

# update sources
sudo apt-get -qq update

# install things:
# libenchant1c2a    pyenchant dependency
# libxml2-dev       python-lxml dependency
# libxslt-dev       python-lxml dependency
# zlib1g-dev        python-lxml dependency
sudo apt-get install -qq -y python3-pip git libenchant-dev libxml2-dev libxslt1-dev

# install requirements using pip
sudo pip3 install -Ur /vagrant/requirements-dev.txt

# create link from project to ~/bot
ln -sf /vagrant /home/vagrant/bot

# create start.sh script
cat > /usr/local/bin/start-bot <<- _EOF_
    #!/usr/bin/env bash
    cd /home/vagrant/bot
    python3 -m cloudbot
_EOF_
chmod +x /usr/local/bin/start-bot
