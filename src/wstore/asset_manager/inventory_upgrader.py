# -*- coding: utf-8 -*-

# Copyright (c) 2017 CoNWeT Lab., Universidad Politécnica de Madrid

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

import math
from requests.exceptions import HTTPError
from threading import Thread

from wstore.models import Context
from wstore.ordering.inventory_client import InventoryClient


class InventoryUpgrader(Thread):

    def __init__(self, asset):
        Thread.__init__(self)
        self._asset = asset

    def run(self):
        context = Context.objects.all()[0]
        client = InventoryClient()

        # Get all the product ids related to the given product specification
        try:
            product_ids = client.get_products(query={
                'productSpecification.id': self._asset.product_id,
                'fields': 'id'
            })
        except HTTPError:
            # Failure reading the available product ids, all upgrades pending
            context.failed_upgrades.append({
                'asset_id': self._asset.pk,
                'pending_products': []
            })
            context.save()
            return

        # Paginate all the products to avoid too large requests
        n_pages = int(math.ceil(len(product_ids)/100.0))

        # TODO: Handle bundles
        missing_upgrades = []
        for page in range(0, n_pages):
            # Get the ids related to the current product page
            offset = page * 100
            page_ids = [p_id['id'] for p_id in product_ids[offset: offset+100]]
            ids = ','.join(page_ids)

            # Get product characteristics field
            try:
                products = client.get_products(query={
                    'id': ids,
                    'fields': 'id, productCharacteristic'
                })
            except HTTPError:
                missing_upgrades.extend(page_ids)
                continue

            # Patch product to include new asset information
            for product in products:
                new_characteristics = [char for char in product['productCharacteristic']
                                       if char['name'].lower() not in ['asset type', 'media type', 'location']]

                new_characteristics.append({
                    'name': 'Media Type',
                    'value': self._asset.content_type
                })

                new_characteristics.append({
                    'name': 'Asset Type',
                    'value': self._asset.resource_type
                })

                new_characteristics.append({
                    'name': 'Location',
                    'value': self._asset.download_link
                })

                try:
                    client.patch_product(product['id'], {
                        'productCharacteristic': new_characteristics
                    })
                except HTTPError:
                    missing_upgrades.append(product['id'])

        if len(missing_upgrades) > 0:
            context.failed_upgrades.append({
                'asset_id': self._asset.pk,
                'pending_products': missing_upgrades
            })
            context.save()
