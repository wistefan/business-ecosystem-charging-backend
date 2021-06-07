FROM ubuntu:16.04

LABEL MAINTAINER="Future Internet Consulting and Development Solutions S.L."

RUN apt-get update && apt-get install -y --fix-missing \
    gcc git wkhtmltopdf xvfb python2.7 python-pip wget \
    python-dev build-essential libssl-dev libffi-dev \
    apache2 libapache2-mod-wsgi && \
    git clone https://github.com/FIWARE-TMForum/business-ecosystem-charging-backend.git && \
    pip install sh

ENV VERSION master

WORKDIR /business-ecosystem-charging-backend

RUN git checkout $VERSION && \
    mkdir ./src/media && \
    mkdir ./src/media/bills && \
    mkdir ./src/media/assets && \
    mkdir ./src/plugins && \
    pip install -r requirements.txt

# Create volumes
VOLUME /business-ecosystem-charging-backend/src/media/bills
VOLUME /business-ecosystem-charging-backend/src/media/assets
VOLUME /business-ecosystem-charging-backend/src/plugins
VOLUME /business-ecosystem-charging-backend/src/user_settings
VOLUME /business-ecosystem-charging-backend/src/wstore/asset_manager/resource_plugins/plugins

WORKDIR /business-ecosystem-charging-backend/src

RUN rm wsgi.py
COPY wsgi.py .

WORKDIR /etc/apache2/
COPY charging.conf ./sites-available

RUN ln -s ../sites-available/charging.conf ./sites-enabled/charging.conf && \
    sed -i "s|Listen 80|Listen 8006|g" ports.conf

WORKDIR /business-ecosystem-charging-backend/src

COPY ./entrypoint.sh /

EXPOSE 8006

ENTRYPOINT ["/entrypoint.sh"]

