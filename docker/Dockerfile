FROM python:2.7

RUN apt-get update && apt-get install -y --fix-missing  mongodb python-pip git wkhtmltopdf xvfb python-dev

RUN git clone https://github.com/FIWARE-TMForum/business-ecosystem-charging-backend.git

RUN pip install sh

WORKDIR business-ecosystem-charging-backend

RUN git checkout develop

# Create required folders
RUN mkdir -p /data/db/
RUN mkdir ./src/media
RUN mkdir ./src/media/bills

ENV WORKSPACE=`pwd`

RUN ./python-dep-install.sh

# Create volumes
VOLUME /data/db
VOLUME ./src/media

WORKDIR src

COPY ./entrypoint.py /
COPY ./entrypoint.sh /

EXPOSE 8004

ENTRYPOINT ["/entrypoint.sh"]

