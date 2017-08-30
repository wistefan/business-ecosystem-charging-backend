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

from bson import ObjectId
from copy import deepcopy
from mock import MagicMock, call
from requests.exceptions import HTTPError

from django.test.testcases import TestCase

from wstore.asset_manager import inventory_upgrader


class InventoryUpgraderTestCase(TestCase):

    tags = ('upgrades', )

    _prev_asset_chars = [{
        'name': 'Media Type',
        'value': 'application/xml'
    }, {
        'name': 'Asset type',
        'value': 'Service'
    }, {
        'name': 'Location',
        'value': 'https://myservice.com/v1'
    }]

    _product1 = {
        'id': '1',
        'productCharacteristic': deepcopy(_prev_asset_chars)
    }

    _product1['productCharacteristic'].append({
        'name': 'speed',
        'value': '100mbps'
    })

    _product2 = {
        'id': '2',
        'productCharacteristic': deepcopy(_prev_asset_chars)
    }

    _product2['productCharacteristic'].append({
        'name': 'speed',
        'value': '20mbps'
    })

    _product3 = {
        'id': '3',
        'productCharacteristic': deepcopy(_prev_asset_chars)
    }

    _product4 = {
        'id': '4',
        'productCharacteristic': deepcopy(_prev_asset_chars)
    }

    _product5 = {
        'id': '5',
        'productCharacteristic': deepcopy(_prev_asset_chars)
    }

    _ctx_pk = '58a447608e05ac5752d96d98'
    _asset_pk = '1111'
    _product_spec_id = '10'
    _new_media_type = 'application/json'
    _new_location = 'https://myservice.com/v2'

    _new_asset_chars = [{
        'name': 'Media Type',
        'value': _new_media_type
    }, {
        'name': 'Asset Type',
        'value': 'Service'
    }, {
        'name': 'Location',
        'value': _new_location
    }]

    def setUp(self):
        # Mock Context
        self._ctx_instance = MagicMock(failed_upgrades=[])
        self._ctx_instance.pk = self._ctx_pk

        inventory_upgrader.Context = MagicMock()
        inventory_upgrader.Context.objects.all.return_value = [self._ctx_instance]

        # Mock Inventory client
        self._client_instance = MagicMock()
        inventory_upgrader.InventoryClient = MagicMock(return_value=self._client_instance)

        # Mock database connector
        self._db = MagicMock()
        inventory_upgrader.get_database_connection = MagicMock(return_value=self._db)

        inventory_upgrader.PAGE_LEN = 2.0

        self._asset = MagicMock()
        self._asset.pk = self._asset_pk
        self._asset.product_id = self._product_spec_id
        self._asset.content_type = self._new_media_type
        self._asset.resource_type = 'Service'
        self._asset.download_link = self._new_location

    def _check_single_get_call(self):
        self._client_instance.get_products.assert_called_once_with(query={
            'productSpecification.id': self._product_spec_id,
            'fields': 'id'
        })

        self.assertEquals(0, self._client_instance.patch_product.call_count)

    def test_inventory_upgrader_no_products(self):
        self._client_instance.get_products.return_value = []

        # Execute the tested method
        upgrader = inventory_upgrader.InventoryUpgrader(self._asset)
        upgrader.run()

        # Check calls
        self.assertEquals([], self._ctx_instance.failed_upgrades)
        self._check_single_get_call()

    def test_inventory_upgrader(self):
        # Mock inventory client methods
        self._client_instance.get_products.side_effect = [
            [{'id': unicode(i)} for i in range(1, 6)],  # First call
            [self._product1, self._product2],  # Second call
            [self._product3, self._product4],  # Third call
            [self._product5]  # Last call
        ]

        # Execute the tested method
        upgrader = inventory_upgrader.InventoryUpgrader(self._asset)
        upgrader.run()

        # Check calls
        self.assertEquals([], self._ctx_instance.failed_upgrades)

        self.assertEquals([
            call(query={
                'productSpecification.id': self._product_spec_id,
                'fields': 'id'
            }),
            call(query={
                'id': '1,2',
                'fields': 'id, productCharacteristic'
            }),
            call(query={
                'id': '3,4',
                'fields': 'id, productCharacteristic'
            }),
            call(query={
                'id': '5',
                'fields': 'id, productCharacteristic'
            }),
        ], self._client_instance.get_products.call_args_list)

        exp_charp1 = deepcopy(self._new_asset_chars)
        exp_charp1.insert(0, {
            'name': 'speed',
            'value': '100mbps'
        })
        exp_charp2 = deepcopy(self._new_asset_chars)
        exp_charp2.insert(0, {
            'name': 'speed',
            'value': '20mbps'
        })

        self.assertEquals([
            call('1', {
                'productCharacteristic': exp_charp1
            }),
            call('2', {
                'productCharacteristic': exp_charp2
            }),
            call('3', {
                'productCharacteristic': self._new_asset_chars
            }),
            call('4', {
                'productCharacteristic': self._new_asset_chars
            }),
            call('5', {
                'productCharacteristic': self._new_asset_chars
            })
        ], self._client_instance.patch_product.call_args_list)

    def test_inventory_upgrader_ids_error(self):
        self._client_instance.get_products.side_effect = HTTPError()
        self._db.wstore_context.find_one_and_update.return_value = False

        # Execute the tested method
        upgrader = inventory_upgrader.InventoryUpgrader(self._asset)
        upgrader.run()

        # Check calls
        self.assertEquals([{
            'asset_id': self._asset_pk,
            'pending_products': []
        }], self._ctx_instance.failed_upgrades)

        self.assertEquals([
            call({'_id': ObjectId(self._ctx_pk)}, {'$set': {'_lock_upg': True}}),
            call({'_id': ObjectId(self._ctx_pk)}, {'$set': {'_lock_upg': False}}),
        ], self._db.wstore_context.find_one_and_update.call_args_list)

        self._ctx_instance.save.assert_called_once_with()
        self._check_single_get_call()

    def test_inventory_upgrader_page_error(self):
        # Mock inventory client methods
        self._client_instance.get_products.side_effect = [
            [{'id': unicode(i)} for i in range(1, 5)],  # First call
            HTTPError(),  # Second call - HTTPError retrieving page
            [self._product3, self._product4],  # Last call
        ]

        self._db.wstore_context.find_one_and_update.return_value = False

        # Execute the tested method
        upgrader = inventory_upgrader.InventoryUpgrader(self._asset)
        upgrader.run()

        # Check calls
        self.assertEquals([{
            'asset_id': self._asset_pk,
            'pending_products': ['1', '2']
        }], self._ctx_instance.failed_upgrades)
        self._ctx_instance.save.assert_called_once_with()

        self.assertEquals([
            call({'_id': ObjectId(self._ctx_pk)}, {'$set': {'_lock_upg': True}}),
            call({'_id': ObjectId(self._ctx_pk)}, {'$set': {'_lock_upg': False}}),
        ], self._db.wstore_context.find_one_and_update.call_args_list)

        self.assertEquals([
            call(query={
                'productSpecification.id': self._product_spec_id,
                'fields': 'id'
            }),
            call(query={
                'id': '1,2',
                'fields': 'id, productCharacteristic'
            }),
            call(query={
                'id': '3,4',
                'fields': 'id, productCharacteristic'
            })
        ], self._client_instance.get_products.call_args_list)

        self.assertEquals([
            call('3', {
                'productCharacteristic': self._new_asset_chars
            }),
            call('4', {
                'productCharacteristic': self._new_asset_chars
            })
        ], self._client_instance.patch_product.call_args_list)

    def test_inventory_upgrader_patch_error(self):
        self._client_instance.get_products.side_effect = [
            [{'id': unicode(i)} for i in range(3, 5)],  # First call
            [self._product3, self._product4],  # Last call
        ]

        self._db.wstore_context.find_one_and_update.side_effect = [True, True, False, False]

        self._client_instance.patch_product.side_effect = [None, HTTPError()]

        # Execute the tested method
        upgrader = inventory_upgrader.InventoryUpgrader(self._asset)
        upgrader.run()

        # Check calls
        self.assertEquals([{
            'asset_id': self._asset_pk,
            'pending_products': ['4']
        }], self._ctx_instance.failed_upgrades)
        self._ctx_instance.save.assert_called_once_with()

        self.assertEquals([
            call({'_id': ObjectId(self._ctx_pk)}, {'$set': {'_lock_upg': True}}),
            call({'_id': ObjectId(self._ctx_pk)}, {'$set': {'_lock_upg': True}}),
            call({'_id': ObjectId(self._ctx_pk)}, {'$set': {'_lock_upg': True}}),
            call({'_id': ObjectId(self._ctx_pk)}, {'$set': {'_lock_upg': False}}),
        ], self._db.wstore_context.find_one_and_update.call_args_list)

        self.assertEquals([
            call(query={
                'productSpecification.id': self._product_spec_id,
                'fields': 'id'
            }),
            call(query={
                'id': '3,4',
                'fields': 'id, productCharacteristic'
            })
        ], self._client_instance.get_products.call_args_list)

        self.assertEquals([
            call('3', {
                'productCharacteristic': self._new_asset_chars
            }),
            call('4', {
                'productCharacteristic': self._new_asset_chars
            })
        ], self._client_instance.patch_product.call_args_list)
