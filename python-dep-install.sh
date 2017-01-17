#!/bin/bash

if [ -d "./virtenv" ]; then
    source virtenv/bin/activate
fi

# Download and install Python dependencies
pip install "pymongo==3.4.0" "paypalrestsdk==1.11.0"
pip install https://github.com/django-nonrel/django/archive/nonrel-1.6.zip 
pip install https://github.com/django-nonrel/djangotoolbox/archive/master.zip
pip install https://github.com/django-nonrel/mongodb-engine/archive/master.zip

pip install "nose==1.3.6" "django-nose==1.4"

pip install "django-crontab==0.6.0"
pip install requests
pip install requests[security]
pip install regex
pip install six
pip install paypalrestsdk
