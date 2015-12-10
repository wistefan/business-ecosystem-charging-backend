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
from django.core.exceptions import ImproperlyConfigured

from nose_parameterized import parameterized
from mock import MagicMock

from django.test import TestCase

from wstore.ordering import ordering_client


class OrderingManagementTestCase(TestCase):

    def setUp(self):
        pass


class OrderingClientTestCase(TestCase):

    tags = ('ordering', 'ordering-client')

    def setUp(self):
        # Mock Context
        ordering_client.Context = MagicMock()
        self._context_inst = MagicMock()
        self._context_inst.local_site.domain = 'http://testdomain.com'
        ordering_client.Context.objects.all.return_value = [self._context_inst]

        # Mock requests
        ordering_client.requests = MagicMock()
        self._response = MagicMock()
        self._response.status_code = 200
        ordering_client.requests.post.return_value = self._response
        ordering_client.requests.patch.return_value = self._response

    def test_ordering_subscription(self):
        client = ordering_client.OrderingClient()

        client.create_ordering_subscription()

        # Check calls
        ordering_client.Context.objects.all.assert_called_once_with()
        ordering_client.requests.post.assert_called_once_with('http://localhost:8080/DSProductOrdering/productOrdering/v2/hub', {
            'callback': 'http://testdomain.com/charging/api/orderManagement/orders'
        })

    def test_ordering_subscription_error(self):
        client = ordering_client.OrderingClient()
        self._response.status_code = 400

        error = None
        try:
            client.create_ordering_subscription()
        except ImproperlyConfigured as e:
            error = e

        self.assertFalse(error is None)
        msg = "It hasn't been possible to create ordering subscription, "
        msg += 'please check that the ordering API is correctly configured '
        msg += 'and that the ordering API is up and running'

        self.assertEquals(msg, unicode(e))

    def test_update_state(self):
        client = ordering_client.OrderingClient()
        client.update_state('1', 'inProgress')

        ordering_client.requests.patch.assert_called_once_with('http://localhost:8080/DSProductOrdering/api/productOrdering/v2/productOrder/1', {
            'state': 'inProgress'
        })

        self._response.raise_for_status.assert_called_once_with()
