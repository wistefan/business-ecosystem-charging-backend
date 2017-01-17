#!/usr/bin/env bash
# Contributed by @Cazaril

# Validate that mandatory parameters has been provided
if [ -z $PAYPAL_CLIENT_ID ]; then
    echo 'PAYPAL_CLIENT_ID environment variable not set'
    exit 1
fi

if [ -z $PAYPAL_CLIENT_SECRET ]; then
    echo 'PAYPAL_CLIENT_SECRET environment variable not set'
    exit 1
fi

if [ -z $BIZ_ECOSYS_PORT ]; then
    echo 'BIZ_ECOSYS_PORT environment variable not set'
    exit 1
fi

if [ -z $BIZ_ECOSYS_HOST ]; then
    echo 'BIZ_ECOSYS_HOST environment variable not set'
    exit 1
fi

if [ -z $ADMIN_EMAIL ]; then
    echo 'ADMIN_EMAIL environment variable not set'
    exit 1
fi

if [ -z $GLASSFISH_HOST ]; then
    echo 'GLASSFISH_HOST environment variable not set'
    exit 1
fi

if [ -z $GLASSFISH_PORT ]; then
    echo 'GLASSFISH_PORT environment variable not set'
    exit 1
fi

service mongodb start

# Configure settings
sed -i "s|PAYPAL_CLIENT_ID = ''|PAYPAL_CLIENT_ID = '$PAYPAL_CLIENT_ID'|g" ./wstore/charging_engine/payment_client/paypal_client.py

sed -i "s|PAYPAL_CLIENT_SECRET = ''|PAYPAL_CLIENT_SECRET = '$PAYPAL_CLIENT_SECRET'|g" ./wstore/charging_engine/payment_client/paypal_client.py

sed -i "s|WSTOREMAIL = 'wstore_email'|WSTOREMAIL = '$ADMIN_EMAIL'|g" ./settings.py

if [[ ! -z $EMAIL_USER ]]; then
    sed -i "s|WSTOREMAILUSER = 'email_user'|WSTOREMAILUSER = '$EMAIL_USER'|g" ./settings.py
fi

if [[ ! -z $EMAIL_PASSWD ]]; then
    sed -i "s|WSTOREMAILPASS = 'wstore_email_passwd'|WSTOREMAILPASS = '$EMAIL_PASSWD'|g" ./settings.py
fi

if [[ ! -z $EMAIL_SERVER ]]; then
    sed -i "s|SMTPSERVER = 'wstore_smtp_server'|SMTPSERVER = '$EMAIL_SERVER'|g" ./settings.py
fi

if [[ ! -z $EMAIL_SERVER_PORT ]]; then
    sed -i "s|SMTPPORT = 587|SMTPPORT = $EMAIL_SERVER_PORT|g" ./settings.py
fi


# Configure services
sed -i "s|CATALOG = 'http://localhost:8080/DSProductCatalog'|CATALOG = 'http://$GLASSFISH_HOST:$GLASSFISH_PORT/DSProductCatalog'|g" services_settings.py

sed -i "s|INVENTORY = 'http://localhost:8080/DSProductInventory'|INVENTORY = 'http://$GLASSFISH_HOST:$GLASSFISH_PORT/DSProductInventory'|g" services_settings.py

sed -i "s|ORDERING = 'http://localhost:8080/DSProductOrdering'|ORDERING = 'http://$GLASSFISH_HOST:$GLASSFISH_PORT/DSProductOrdering'|g" ./services_settings.py

sed -i "s|BILLING = 'http://localhost:8080/DSBillingManagement'|BILLING = 'http://$GLASSFISH_HOST:$GLASSFISH_PORT/DSBillingManagement'|g" ./services_settings.py

sed -i "s|RSS = 'http://localhost:8080/DSRevenueSharing'|RSS = 'http://$GLASSFISH_HOST:$GLASSFISH_PORT/DSRevenueSharing'|g" ./services_settings.py

sed -i "s|USAGE = 'http://localhost:8080/DSUsageManagement'|USAGE = 'http://$GLASSFISH_HOST:$GLASSFISH_PORT/DSUsageManagement'|g" ./services_settings.py

sed -i "s|AUTHORIZE_SERVICE = 'http://localhost:8004/authorizeService/apiKeys'|AUTHORIZE_SERVICE = 'http://$BIZ_ECOSYS_HOST:$BIZ_ECOSYS_PORT/authorizeService/apiKeys'|g" ./services_settings.py

# Ensure mongodb is running
echo "Testing MongoDB connection"
exec 10<>/dev/tcp/127.0.0.1/27017
MONGOST=$?
I=0

while [[ $MONGOST -ne 0 && $I -lt 50 ]]; do
    echo "Mongo is not responding yet"
    echo "Retrying in a few seconds..."
    sleep 5

    exec 10<>/dev/tcp/127.0.0.1/27017
    MONGOST=$?
    I=$I+1
done

exec 10>&- # close output connection
exec 10<&- # close input connection

if [[ $I -eq 50 ]]; then
    echo "It has not been posible to connect to the database"
    exit 1
fi

echo "Connected to Mongo"

python ./manage.py createsite external http://$BIZ_ECOSYSTEM_HOST:$BIZ_ECOSYSTEM_PORT/
python ./manage.py createsite internal http://127.0.0.1:8006/

echo "Starting charging server"
service apache2 restart

while true; do sleep 1000; done
