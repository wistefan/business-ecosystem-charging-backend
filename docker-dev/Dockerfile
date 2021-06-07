FROM ubuntu:16.04

MAINTAINER CoNWeT Lab. Universidad Politécnica de Madrid

RUN apt-get update && apt-get install -y --fix-missing \
    gcc git wkhtmltopdf xvfb python2.7 python-pip \
    python-dev build-essential libssl-dev libffi-dev \
    apache2 libapache2-mod-wsgi vim && \
    pip install sh && \
    pip install cryptography==3.2 && \
    mkdir -p business-ecosystem-charging-backend/src

WORKDIR business-ecosystem-charging-backend

COPY ./python-dep-install.sh .

ENV WORKSPACE=`pwd`

# Install python dependencies
RUN ./python-dep-install.sh && \
    echo "#!/bin/bash" > /entrypoint.sh && \
    echo "while true; do sleep 1000; done" >> /entrypoint.sh && chmod +x /entrypoint.sh

# Create volume for the software under development
VOLUME /business-ecosystem-charging-backend/src

EXPOSE 8006

ENTRYPOINT ["/entrypoint.sh"]

