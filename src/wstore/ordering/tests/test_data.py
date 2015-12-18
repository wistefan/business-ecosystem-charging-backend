# -*- coding: utf-8 -*-

# Copyright (c) 2015 CoNWeT Lab., Universidad Politécnica de Madrid

# This file is part of WStore.

# WStore is free software: you can redistribute it and/or modify
# it under the terms of the European Union Public Licence (EUPL)
# as published by the European Commission, either version 1.1
# of the License, or (at your option) any later version.

# WStore is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# European Union Public Licence for more details.

# You should have received a copy of the European Union Public Licence
# along with WStore.
# If not, see <https://joinup.ec.europa.eu/software/page/eupl/licence-eupl>.


from __future__ import unicode_literals


OFFERING_PRODUCT = {
    "id": "5",
    "name": "Example offering",
    "version": "1.0",
    "description": "Example offering description",
    "href": "http://localhost:8004/DSProductCatalog/api/catalogManagement/v2/productOffering/20:(2.0)",
    "productSpecification": {
        "href": "http://producturl.com/"
    },
    "relatedParty": [{
        "id": "test_user",
        "role": "Owner"
    }, {
        "id": "test_user2",
        "role": "Partner"
    }]
}

BASIC_ORDER = {
    "id": "12",
    "state": "Acknowledged",
    "description": "",
    "orderItem": [
      {
         "id": "1",
         "action": "add",
         "billingAccount": [{
               "id": "1789",
               "href": "http://serverlocation:port/billingManagement/billingAccount/1789"
         }],
         "productOffering": {
            "id": "20",
            "href": "http://localhost:8004/DSProductCatalog/api/catalogManagement/v2/productOffering/20:(2.0)"
         },
         "product": {
             "productPrice": [{
             "priceType": "one time",
             "unitOfMeasure": "",
             "price": {
                "taxIncludedAmount": "12.00",
                "dutyFreeAmount": "10.00",
                "taxRate": "20.00",
                "currencyCode": "EUR",
                "percentage": 0
             },
             "recurringChargePeriod": "",
             "name": "One Time",
             "validFor": {
                 "startDateTime": "2013-04-19T20:42:23.000+0000",
                 "endDateTime": "2013-06-19T04:00:00.000+0000"
             }
            }]
         }
      }
   ]
}

RECURRING_ORDER = {
    "id": "12",
    "state": "Acknowledged",
    "orderItem": [
      {
         "id": "1",
         "action": "add",
         "billingAccount": [{
               "id": "1789",
               "href": "http://serverlocation:port/billingManagement/billingAccount/1789"
         }],
         "productOffering": {
            "id": "20",
            "href": "http://localhost:8004/DSProductCatalog/api/catalogManagement/v2/productOffering/20:(2.0)"
         },
         "product": {
             "productPrice": [{
             "priceType": "recurring",
             "unitOfMeasure": "",
             "price": {
                "taxIncludedAmount": "12.00",
                "dutyFreeAmount": "10.00",
                "taxRate": "20.00",
                "currencyCode": "EUR",
                "percentage": 0
             },
             "recurringChargePeriod": "monthly",
             "name": "Recurring Monthly Charge",
             "description": "A monthly recurring payment",
             "validFor": {
                 "startDateTime": "2013-04-19T20:42:23.000+0000",
                 "endDateTime": "2013-06-19T04:00:00.000+0000"
             }
            }]
         }
      }
   ]
}

USAGE_ORDER = {
    "id": "12",
    "state": "Acknowledged",
    "orderItem": [
      {
         "id": "1",
         "action": "add",
         "billingAccount": [{
               "id": "1789",
               "href": "http://serverlocation:port/billingManagement/billingAccount/1789"
         }],
         "productOffering": {
            "id": "20",
            "href": "http://localhost:8004/DSProductCatalog/api/catalogManagement/v2/productOffering/20:(2.0)"
         },
         "product": {
             "productPrice": [{
             "priceType": "Usage",
             "unitOfMeasure": "megabyte",
             "price": {
                "taxIncludedAmount": "12.00",
                "dutyFreeAmount": "10.00",
                "taxRate": "20.00",
                "currencyCode": "EUR",
                "percentage": 0
             },
             "recurringChargePeriod": "",
             "name": "Recurring Monthly Charge",
             "description": "A monthly recurring payment",
             "validFor": {
                 "startDateTime": "2013-04-19T20:42:23.000+0000",
                 "endDateTime": "2013-06-19T04:00:00.000+0000"
             }
            }]
         }
      }
   ]
}

FREE_ORDER = {
    "id": "12",
    "state": "Acknowledged",
    "orderItem": [
      {
         "id": "1",
         "action": "add",
         "billingAccount": [{
               "id": "1789",
               "href": "http://serverlocation:port/billingManagement/billingAccount/1789"
         }],
         "productOffering": {
            "id": "20",
            "href": "http://localhost:8004/DSProductCatalog/api/catalogManagement/v2/productOffering/20:(2.0)"
         },
         "product": {
         }
      }
   ]
}

NOPRODUCT_ORDER = {
    "id": "12",
    "state": "Acknowledged",
    "orderItem": [
      {
         "id": "1",
         "action": "add",
         "billingAccount": [{
               "id": "1789",
               "href": "http://serverlocation:port/billingManagement/billingAccount/1789"
         }],
         "productOffering": {
            "id": "20",
            "href": "http://localhost:8004/DSProductCatalog/api/catalogManagement/v2/productOffering/20:(2.0)"
         },
      }
   ]
}

INVALID_STATE_ORDER = {
    "id": "12",
    "state": "inProgress"
}

INVALID_MODEL_ORDER = {
    "id": "12",
    "state": "Acknowledged",
    "orderItem": [
      {
         "id": "1",
         "action": "add",
         "product": {
             "productPrice": [{
                 "price": {
                 },
                 "priceType": "Invalid",
             }]
         }
      }
   ]
}