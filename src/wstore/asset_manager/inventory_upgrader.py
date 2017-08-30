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
from bson import ObjectId
from requests.exceptions import HTTPError
from threading import Thread

from wstore.models import Context
from wstore.ordering.inventory_client import InventoryClient
from wstore.store_commons.database import get_database_connection


PAGE_LEN = 100.0


class InventoryUpgrader(Thread):

    def __init__(self, asset):
        Thread.__init__(self)
        self._asset = asset
        self._client = InventoryClient()

    def _save_failed(self, pending):
        # The failed upgrades list may be upgraded by other threads or other server instances
        # In this case context must be accessed as a shared resource
        context_id = Context.objects.all()[0].pk

        db = get_database_connection()
        locked = db.wstore_context.find_one_and_update(
            {'_id': ObjectId(context_id)},
            {'$set': {'_lock_upg': True}}
        )

        while locked:
            locked = db.wstore_context.find_one_and_update(
                {'_id': ObjectId(context_id)},
                {'$set': {'_lock_upg': True}}
            )

        # At this point only the current thread can modify the list of pending upgrades
        context = Context.objects.all()[0]
        context.failed_upgrades.append({
            'asset_id': self._asset.pk,
            'pending_products': pending
        })
        context.save()

        db.wstore_context.find_one_and_update(
            {'_id': ObjectId(context_id)},
            {'$set': {'_lock_upg': False}}
        )

    def upgrade_products(self, product_ids, id_filter):
        n_pages = int(math.ceil(len(product_ids)/PAGE_LEN))

        # TODO: Handle bundles
        missing_upgrades = []
        for page in range(0, n_pages):
            # Get the ids related to the current product page
            offset = page * int(PAGE_LEN)

            page_ids = [id_filter(p_id) for p_id in product_ids[offset: offset + int(PAGE_LEN)]]
            ids = ','.join(page_ids)

            # Get product characteristics field
            try:
                products = self._client.get_products(query={
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
                    self._client.patch_product(product['id'], {
                        'productCharacteristic': new_characteristics
                    })
                except HTTPError:
                    missing_upgrades.append(product['id'])

        return missing_upgrades if len(missing_upgrades) > 0 else None

    def upgrade_asset_products(self):
        # Get all the product ids related to the given product specification
        try:
            product_ids = self._client.get_products(query={
                'productSpecification.id': self._asset.product_id,
                'fields': 'id'
            })
        except HTTPError:
            # Failure reading the available product ids, all upgrades pending
            return []

        # TODO: Handle bundles
        return self.upgrade_products(product_ids, lambda p_id: p_id['id'])

    def run(self):
        # Upgrade all the products related to the provided asset
        missing_upgrades = self.upgrade_asset_products()

        if missing_upgrades is not None:
            self._save_failed(missing_upgrades)
