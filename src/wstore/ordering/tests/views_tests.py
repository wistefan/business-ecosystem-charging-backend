# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2016 CoNWeT Lab., Universidad Politécnica de Madrid

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

import json
from mock import MagicMock, call
from nose_parameterized import parameterized

from django.test import TestCase

from wstore.ordering import views
from wstore.ordering.errors import OrderingError


class OrderingCollectionTestCase(TestCase):

    tags = ('ordering', 'ordering-view')

    def _missing_billing(self):
        self.request.user.userprofile.current_organization.tax_address = {}

    def _ordering_error(self):
        views.OrderingManager().process_order.side_effect = OrderingError('order error')

    def _exception(self):
        views.OrderingManager().process_order.side_effect = Exception('Unexpected error')

    @parameterized.expand([
        ('basic', {
            'id': 1
        }, None, 200, {
            'result': 'correct',
            'message': 'OK'
        }),
        ('redirection', {
            'id': 1
        }, 'http://redirection.com/', 200, {
            'redirectUrl': 'http://redirection.com/'
        }),
        ('invalid_data', 'invalid', None, 400, {
            'result': 'error',
            'message': 'The provided data is not a valid JSON object'
        }, False),
        ('missing_billing', {}, None, 400, {
            'result': 'error',
            'message': 'The customer has not defined a billing address'
        }, False, True, _missing_billing),
        ('ordering_error', {}, None, 400, {
            'result': 'error',
            'message': 'OrderingError: order error'
        }, True, True, _ordering_error),
        ('exception', {}, None, 400, {
            'result': 'error',
            'message': 'Your order could not be processed'
        }, True, True, _exception)
    ])
    def test_create_order(self, name, data, redirect_url, exp_code, exp_response, called=True, failed=False, side_effect=None):
        # Create mocks
        views.OrderingManager = MagicMock()
        views.OrderingManager().process_order.return_value = redirect_url

        views.OrderingClient = MagicMock()

        self.request = MagicMock()
        self.request.META.get.return_value = 'application/json'
        self.request.user.is_anonymous.return_value = False
        self.request.user.userprofile.current_organization.tax_address = {
            'street': 'fake'
        }
        if isinstance(data, dict):
            data = json.dumps(data)
        self.request.body = data

        if side_effect is not None:
            side_effect(self)

        collection = views.OrderingCollection(permitted_methods=('POST',))
        response = collection.create(self.request)
        body = json.loads(response.content)

        self.assertEquals(exp_code, response.status_code)
        self.assertEquals(exp_response, body)

        if called:
            views.OrderingManager().process_order.assert_called_once_with(self.request.user, json.loads(data))

        if failed:
            self.assertEquals(
                [call(json.loads(data), 'InProgress'), call(json.loads(data), 'Failed')],
                views.OrderingClient().update_state.call_args_list)


class InventoryCollectionTestCase(TestCase):
    pass