FROM ubuntu:16.04

LABEL Author="CoNWeT Lab. Universidad Politécnica de Madrid"

RUN apt-get update && apt-get install -y --fix-missing \
    gcc git wkhtmltopdf xvfb python2.7 python-pip wget \
    python-dev build-essential libssl-dev libffi-dev \
    apache2 libapache2-mod-wsgi && \
    git clone https://github.com/FIWARE-TMForum/business-ecosystem-charging-backend.git && \
    pip install sh

ENV VERSION develop

WORKDIR /business-ecosystem-charging-backend

RUN git checkout $VERSION && \
    mkdir ./src/media && \
    mkdir ./src/media/bills && \
    mkdir ./src/media/assets && \
    mkdir ./src/plugins && \
    mkdir ./src/user_settings && \
    cp ./src/settings.py ./src/user_settings/settings.py && \
    cp ./src/services_settings.py ./src/user_settings/services_settings.py

ENV WORKSPACE=`pwd`

# Install dependencies and configure system to support volume settings
RUN ./python-dep-install.sh && \
    echo "from user_settings.settings import *" > ./src/settings.py && \
    echo "BASEDIR = path.dirname(path.abspath(__file__))" >> settings.py && \
    echo "MEDIA_ROOT = path.join(BASEDIR, MEDIA_DIR)" >> settings.py && \
    echo "BILL_ROOT = path.join(MEDIA_ROOT, 'bills')" >> settings.py

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

