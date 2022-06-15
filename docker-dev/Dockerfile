FROM ubuntu:20.04

LABEL Maintainer="Future Internet Consulting and Development Solutions S.L."

COPY requirements.txt requirements.txt
COPY dev-requirements.txt dev-requirements.txt

RUN apt-get update

#RUN DEBIAN_FRONTEND="noninteractive" apt-get -y install wkhtmltopdf
RUN apt-get -y install python3 python3-pip
RUN apt-get -y install vim
RUN apt-get -y install xvfb
RUN pip3 install -r requirements.txt && pip3 install -r dev-requirements.txt
RUN mkdir -p business-ecosystem-charging-backend/src
RUN echo "#!/bin/bash" > /entrypoint.sh
RUN echo "while true; do sleep 1000; done" >> /entrypoint.sh && chmod +x /entrypoint.sh

# Create volume for the software under development
VOLUME /business-ecosystem-charging-backend/src

EXPOSE 8006

ENTRYPOINT ["/entrypoint.sh"]
