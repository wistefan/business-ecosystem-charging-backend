#!/usr/bin/env bash
# Contributed by @Cazaril

if [ -z $PAYPAL_CLIENT_ID ]; then
    echo "$PAYPAL_CLIENT_ID environment variable not set"
exit 1
fi

if [ -z $PAYPAL_CLIENT_SECRET ]; then
    echo "$PAYPAL_CLIENT_SECRET environment variable not set"
exit 1
fi

if [ -z $BIZ_ECOSYS_PORT ]; then
    echo "$BIZ_ECOSYS_PORT environment variable not set"
exit 1
fi

if [ -z $BIZ_ECOSYS_HOST ]; then
    echo "$BIZ_ECOSYS_HOST environment variable not set"
exit 1
fi

if [ -z $WSTOREMAIL ]; then
    echo "$WSTOREMAIL environment variable not set"
exit 1
fi

if [ -z $GLASSFISH_HOST ]; then
    echo "$GLASSFISH_HOST environment variable not set"
exit 1
fi

if [ -z $GLASSFISH_PORT ]; then
    echo "$GLASSFISH_PORT environment variable not set"
exit 1
fi

mongod &

sleep 15

sed -i "s|PAYPAL_CLIENT_ID = [\w-]*|PAYPAL_CLIENT_ID = $PAYPAL_CLIENT_ID|g" ./wstore/charging_engine/payment_client/paypal_client.py

sed -i "s|PAYPAL_CLIENT_SECRET = [\w-]*|PAYPAL_CLIENT_SECRET = $PAYPAL_CLIENT_SECRET|g" ./wstore/charging_engine/payment_client/paypal_client.py


sed -i "s|WSTOREMAIL = <email>|WSTOREMAIL = $WSTOREMAIL|g" ./settings.py

sed -i "s|WSTOREMAILUSER = <mail_user|WSTOREMAILUSER = $WSTOREMAILUSER|g" ./settings.py

sed -i "s|WSTOREMAILPASS = <email_passwd>|WSTOREMAILPASS = $WSTOREMAILPASS|g" ./settings.py

sed -i "s|PAYMENT_METHOD = None|PAYMENT_METHOD = 'paypal'|g" ./settings.py

sed -i "s|INVENTORY = 'http://localhost:8080/DSProductInventory'|INVENTORY = 'http://$GLASSFISH_HOST:$GLASSFISH_PORT/DSProductInventory'|g" services_settings.py

sed -i "s|ORDERING = 'http://localhost:8080/DSProductOrdering'|ORDERING = 'http://$GLASSFISH_HOST:$GLASSFISH_PORT/DSProductOrdering'|g" ./services_settings.py

sed -i "s|BILLING = 'http://localhost:8080/DSBillingManagement'|BILLING = 'http://$GLASSFISH_HOST:$GLASSFISH_PORT/DSBillingManagement'|g" ./services_settings.py

sed -i "s|RSS = 'http://localhost:8080/DSRevenueSharing'|RSS = 'http://$GLASSFISH_HOST:$GLASSFISH_PORT/DSRevenueSharing'|g" ./services_settings.py

sed -i "s|USAGE = 'http://localhost:8080/DSUsageManagement'|USAGE = 'http://$GLASSFISH_HOST:$GLASSFISH_PORT/DSUsageManagement'|g" ./services_settings.py

sed -i "s|AUTHORIZE_SERVICE = 'http://localhost:8004/authorizeService/apiKeys'|AUTHORIZE_SERVICE = 'http://$BIZ_ECOSYS_HOST:$BIZ_ECOSYS_PORT/authorizeService/apiKeys'|g" ./services_settings.py

python /entrypoint.py

python ./manage.py runserver 8004