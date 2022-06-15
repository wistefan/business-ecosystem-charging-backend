FROM ubuntu:20.04

LABEL MAINTAINER="Future Internet Consulting and Development Solutions S.L."

ENV LOGLEVEL=info
ENV VERSION=master
ARG DEBIAN_FRONTEND=noninteractive

RUN mkdir /opt/business-ecosystem-charging-backend/
WORKDIR /opt/business-ecosystem-charging-backend/

COPY requirements.txt requirements.txt
COPY dev-requirements.txt dev-requirements.txt
COPY src/ src/

RUN apt-get update && apt-get -y install python3 python3-pip gcc git wkhtmltopdf xvfb wget && \
    pip3 install -r requirements.txt && pip3 install -r dev-requirements.txt && \
    mkdir ./src/media && mkdir ./src/media/bills && mkdir ./src/media/assets && mkdir ./src/plugins

# Create volumes
VOLUME /opt/business-ecosystem-charging-backend/src/media/bills
VOLUME /opt/business-ecosystem-charging-backend/src/media/assets
VOLUME /opt/business-ecosystem-charging-backend/src/plugins
VOLUME /opt/business-ecosystem-charging-backend/src/wstore/asset_manager/resource_plugins/plugins

WORKDIR /opt/business-ecosystem-charging-backend/src

COPY ./docker/entrypoint.sh /

EXPOSE 8006

ENTRYPOINT ["/entrypoint.sh"]

