FROM ubuntu:16.04

RUN apt-get update && apt-get install -y --fix-missing \
    gcc mongodb git wkhtmltopdf xvfb python2.7 python-pip \
    python-dev build-essential libssl-dev libffi-dev

RUN git clone https://github.com/FIWARE-TMForum/business-ecosystem-charging-backend.git

RUN pip install sh

WORKDIR business-ecosystem-charging-backend

RUN git checkout develop

# Create required folders
RUN mkdir -p /data/db/
RUN mkdir ./src/media
RUN mkdir ./src/media/bills
RUN mkdir ./src/media/assets

ENV WORKSPACE=`pwd`

RUN ./python-dep-install.sh

# Create volumes
VOLUME /data/db
VOLUME /business-ecosystem-charging-backend/src/media/bills
VOLUME /business-ecosystem-charging-backend/src/media/assets

WORKDIR src

COPY ./entrypoint.sh /

EXPOSE 8006

ENTRYPOINT ["/entrypoint.sh"]

