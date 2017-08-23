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
from threading import Thread

from ordering.inventory_client import InventoryClient


class InventoryUpgrader(Thread):

    def __init__(self, asset):
        Thread.__init__(self)
        self._asset = asset

    def run(self):
        client = InventoryClient()

        # Get all the product ids related to the given product specification
        product_ids = client.get_products(query={
            'productSpecification.id': self._asset.product_id,
            'fields': 'id'
        })

        # Paginate all the products to avoid too large requests
        n_pages = int(math.ceil(len(product_ids)/100.0))

        # TODO: Handle bundles
        for page in range(0, n_pages):
            # Get the ids related to the current product page
            offset = page * 100
            ids = ','.join([p_id['id'] for p_id in product_ids[offset: offset+100]])

            # Get product characteristics field
            products = client.get_products(query={
                'id': ids,
                'fields': 'id, productCharacteristic'
            })

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

                client.patch_product(product['id'], {
                    'productCharacteristic': new_characteristics
                })
