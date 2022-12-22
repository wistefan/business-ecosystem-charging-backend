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

# Check that the settings files have been included
if [ ! -f /opt/business-ecosystem-charging-backend/src/settings.py ]; then
    echo "Missing settings.py file"
    exit 1
fi

if [ ! -f /opt/business-ecosystem-charging-backend/src/services_settings.py ]; then
    echo "Missing services_settings.py file"
    exit 1
fi

if [ ! -f /opt/business-ecosystem-charging-backend/src/__init__.py ]; then
    touch /opt/business-ecosystem-charging-backend/src/__init__.py
fi

# Create __init__.py file if not present (a volume has been bound)
if [ ! -f /opt/business-ecosystem-charging-backend/src/wstore/asset_manager/resource_plugins/plugins/__init__.py ]; then
    touch /opt/business-ecosystem-charging-backend/src/wstore/asset_manager/resource_plugins/plugins/__init__.py
fi

# Ensure mongodb is running
# Get MongoDB host and port from settings

if [ -z ${BAE_CB_MONGO_SERVER} ]; then
    MONGO_HOST=`grep -o "'host':.*" ./settings.py | grep -o ": '.*'" | grep -oE "[^:' ]+"`

    if [ -z ${MONGO_HOST} ]; then
        MONGO_HOST=localhost
    fi
else
    MONGO_HOST=${BAE_CB_MONGO_SERVER}
fi

if [ -z ${BAE_CB_MONGO_PORT} ]; then
    MONGO_PORT=`grep -o "'port':.*" ./settings.py | grep -o ": '.*'" | grep -oE "[^:' ]+"`

    if [ -z ${MONGO_PORT} ]; then
        MONGO_PORT=27017
    fi
else
    MONGO_PORT=${BAE_CB_MONGO_PORT}
fi

test_connection "MongoDB" ${MONGO_HOST} ${MONGO_PORT}

# Check that the required APIs are running
if [ -z ${BAE_CB_CATALOG} ]; then
    APIS_HOST=`grep "CATALOG =.*" ./services_settings.py | grep -o "://.*:" | grep -oE "[^:/]+"`
    APIS_PORT=`grep "CATALOG =.*" ./services_settings.py | grep -oE ":[0-9]+" | grep -oE "[^:/]+"`
else
    APIS_HOST=`echo ${BAE_CB_CATALOG} | grep -o "://.*:" | grep -oE "[^:/]+"`
    APIS_PORT=`echo ${BAE_CB_CATALOG} | grep -oE ":[0-9]+" | grep -oE "[^:/]+"`
fi

test_connection "APIs" ${APIS_HOST} ${APIS_PORT}

# Check that the RSS is running
if [ -z ${BAE_CB_RSS} ]; then
    RSS_HOST=`grep "RSS =.*" ./services_settings.py | grep -o "://.*:" | grep -oE "[^:/]+"`
    RSS_PORT=`grep "RSS =.*" ./services_settings.py | grep -oE ":[0-9]+" | grep -oE "[^:/]+"`
else
    RSS_HOST=`echo ${BAE_CB_RSS} | grep -o "://.*:" | grep -oE "[^:/]+"`
    RSS_PORT=`echo ${BAE_CB_RSS} | grep -oE ":[0-9]+" | grep -oE "[^:/]+"`
fi

test_connection "RSS" ${RSS_HOST} ${RSS_PORT}

# Check that inventory service is running
wget http://${APIS_HOST}:${APIS_PORT}/DSProductInventory
STATUS=$?
I=0
while [[ ${STATUS} -ne 0  && ${I} -lt 50 ]]; do
    echo "Inventory API not ready retrying in 5 seconds..."

    sleep 5
    wget http://${APIS_HOST}:${APIS_PORT}/DSProductInventory
    STATUS=$?

    I=${I}+1
done

# Check that RSS service is running
wget http://${RSS_HOST}:${RSS_PORT}/DSRevenueSharing
STATUS=$?
I=0
while [[ ${STATUS} -ne 6  && ${I} -lt 50 ]]; do
    echo "RSS API not ready retrying in 5 seconds..."

    echo "===============> ${STATUS}"
    sleep 5
    wget http://${RSS_HOST}:${RSS_PORT}/DSRevenueSharing
    STATUS=$?

    I=${I}+1
done

echo "Starting charging server"

python3 manage.py migrate
echo Mongo migration
echo 'mongodb-migrate --host ${MONGO_HOST} --port ${MONGO_PORT} --database ${BAE_CB_MONGO_DB} --username ${BAE_CB_MONGO_USER} --password ${BAE_CB_MONGO_PASS} --migrations migrations'
mongodb-migrate --host ${MONGO_HOST} --port ${MONGO_PORT} --database ${BAE_CB_MONGO_DB} --username ${BAE_CB_MONGO_USER} --password ${BAE_CB_MONGO_PASS} --migrations migrations
gunicorn wsgi:application --workers 1 --forwarded-allow-ips "*" --log-file - --bind 0.0.0.0:8006 --log-level ${LOGLEVEL}
