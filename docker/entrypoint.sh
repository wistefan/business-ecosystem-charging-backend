#!/usr/bin/env bash

function test_connection {
    echo "Testing $1 connection"
    exec 10<>/dev/tcp/$2/$3
    STATUS=$?
    I=0

    while [[ ${STATUS} -ne 0  && ${I} -lt 50 ]]; do
        echo "Connection refused, retrying in 5 seconds..."
        sleep 5

        if [[ ${STATUS} -ne 0 ]]; then
            exec 10<>/dev/tcp/$2/$3
            STATUS=$?

        fi
        I=${I}+1
    done

    exec 10>&- # close output connection
    exec 10<&- # close input connection

    if [[ ${STATUS} -ne 0 ]]; then
        echo "It has not been possible to connect to $1"
        exit 1
    fi

    echo "$1 connection, OK"
}

# Validate that mandatory parameters has been provided
if [ -z $PAYPAL_CLIENT_ID ]; then
    echo 'PAYPAL_CLIENT_ID environment variable not set'
    exit 1
fi

if [ -z $PAYPAL_CLIENT_SECRET ]; then
    echo 'PAYPAL_CLIENT_SECRET environment variable not set'
    exit 1
fi

# Check that the settings files have been included
if [ ! -f /business-ecosystem-charging-backend/src/user_settings/settings.py ]; then
    echo "Missing settings.py file"
    exit 1
fi

if [ ! -f /business-ecosystem-charging-backend/src/user_settings/services_settings.py ]; then
    echo "Missing services_settings.py file"
    exit 1
fi

if [ ! -f /business-ecosystem-charging-backend/src/user_settings/__init__.py ]; then
    touch /business-ecosystem-charging-backend/src/user_settings/__init__.py
fi

# Configure PayPal settings
sed -i "s|PAYPAL_CLIENT_ID = ''|PAYPAL_CLIENT_ID = '$PAYPAL_CLIENT_ID'|g" ./wstore/charging_engine/payment_client/paypal_client.py
sed -i "s|PAYPAL_CLIENT_SECRET = ''|PAYPAL_CLIENT_SECRET = '$PAYPAL_CLIENT_SECRET'|g" ./wstore/charging_engine/payment_client/paypal_client.py

# Ensure mongodb is running
# Get MongoDB host and port from settings
MONGO_HOST=`grep -o "'HOST':.*" ./user_settings/settings.py | grep -o ": '.*'" | grep -oE "[^:' ]+"`

if [ -z ${MONGO_HOST} ]; then
    MONGO_HOST=localhost
fi

MONGO_PORT=`grep -o "'PORT':.*" ./user_settings/settings.py | grep -o ": '.*'" | grep -oE "[^:' ]+"`

if [ -z ${MONGO_PORT} ]; then
    MONGO_PORT=27017
fi

test_connection "MongoDB" ${MONGO_HOST} ${MONGO_PORT}

# Check that the required APIs are running
APIS_HOST=`grep "CATALOG =.*" ./user_settings/services_settings.py | grep -o "://.*:" | grep -oE "[^:/]+"`
APIS_PORT=`grep "CATALOG =.*" ./user_settings/services_settings.py | grep -oE ":[0-9]+" | grep -oE "[^:/]+"`

test_connection "APIs" ${APIS_HOST} ${APIS_PORT}

# Check that the RSS is running
RSS_HOST=`grep "RSS =.*" ./user_settings/services_settings.py | grep -o "://.*:" | grep -oE "[^:/]+"`
RSS_PORT=`grep "RSS =.*" ./user_settings/services_settings.py | grep -oE ":[0-9]+" | grep -oE "[^:/]+"`
test_connection "RSS" ${RSS_HOST} ${RSS_PORT}

echo "Starting charging server"
service apache2 restart

while true; do sleep 1000; done
