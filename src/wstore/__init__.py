# -*- coding: utf-8 -*-

# Copyright (c) 2016 CoNWeT Lab., Universidad Politécnica de Madrid

# This file belongs to the business-charging-backend
# of the Business API Ecosystem.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import sys

from django.conf import settings

from wstore.models import Context
from wstore.ordering.inventory_client import InventoryClient
from wstore.rss_adaptor.rss_manager import ProviderManager


testing = sys.argv[1:2] == ['test']

if not testing and Context.objects.all() and Context.objects.all()[0].local_site is not None:
    inventory = InventoryClient()
    inventory.create_inventory_subscription()

    # Create RSS default aggregator and provider
    credentials = {
        'user': settings.STORE_NAME,
        'roles': ['provider'],
        'email': settings.WSTOREMAIL
    }
    prov_manager = ProviderManager(credentials)

    try:
        prov_manager.register_aggregator({
            'aggregatorId': settings.WSTOREMAIL,
            'aggregatorName': settings.STORE_NAME,
            'defaultAggregator': True
        })
    except Exception as e:  # If the error is a conflict means that the aggregator is already registered
        if e.response.status_code != 409:
            raise e
