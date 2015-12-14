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

from __future__ import absolute_import

import json
import wstore.store_commons.utils.http
from bson.objectid import ObjectId

from mock import MagicMock, call
from nose_parameterized import parameterized

from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings

from wstore.charging_engine import charging_engine
from wstore.charging_engine import views
from wstore.store_commons.utils.testing import decorator_mock


def mock_payment_client(self, module):
    # Mock payment client
    module.importlib = MagicMock()
    module_mock = MagicMock()
    self._payment_class = MagicMock()
    module_mock.PaymentClient = self._payment_class

    self._payment_inst = MagicMock()
    self._payment_class.return_value = self._payment_inst
    module.importlib.import_module.return_value = module_mock


class ChargingEngineTestCase(TestCase):

    tags = ('ordering', 'charging-engine')
    _paypal_url = 'http://paypalurl.com'

    def setUp(self):
        # Mock order
        self._order = MagicMock()

        # Mock payment client
        mock_payment_client(self, charging_engine)
        self._payment_inst.get_checkout_url.return_value = self._paypal_url

        # Mock threading
        charging_engine.threading = MagicMock()

        self._thread = MagicMock()
        charging_engine.threading.Timer.return_value = self._thread

        # Mock invoice builder
        charging_engine.InvoiceBuilder = MagicMock()
        self._invoice_inst = MagicMock()
        charging_engine.InvoiceBuilder.return_value = self._invoice_inst

    def _get_single_payment(self):
        return {
            'general_currency': 'EUR',
            'single_payment': [{
                'value': '12',
                'unit': 'one time',
                'tax_rate': '20.00',
                'duty_free': '10.00'
            }]
        }

    def _get_subscription(self):
        return {
            'general_currency': 'EUR',
            'subscription': [{
                'value': '12.00',
                'unit': 'monthly',
                'tax_rate': '20.00',
                'duty_free': '10.00'
            }]
        }

    def _set_initial_contracts(self):
        contract1 = MagicMock()
        contract1.offering.description = 'Offering 1 description'
        contract1.item_id = '1'
        contract1.pricing_model = self._get_single_payment()

        contract2 = MagicMock()
        contract2.offering.description = 'Offering 2 description'
        contract2.item_id = '2'
        contract2.pricing_model = self._get_subscription()

        self._order.contracts = [contract1, contract2]

        return [{
            'price': '12.00',
            'description': 'Offering 1 description',
            'currency': 'EUR',
            'related_model': {
                'single_payment': [{
                    'value': '12',
                    'unit': 'one time',
                    'tax_rate': '20.00',
                    'duty_free': '10.00'
                }]
            },
            'item': '1'
        }, {
            'price': '12.00',
            'description': 'Offering 2 description',
            'currency': 'EUR',
            'related_model': {
                'subscription': [{
                    'value': '12.00',
                    'unit': 'monthly',
                    'tax_rate': '20.00',
                    'duty_free': '10.00'
                }]
            },
            'item': '2'
        }]

    def _set_free_contract(self):
        contract = MagicMock()
        contract.offering.description = 'Offering description'
        contract.item_id = '1'
        contract.pricing_model = {}

        self._order.contracts = [contract]

    @override_settings(PAYMENT_METHOD=None)
    def test_initial_payment(self,):

        self._order.state = 'pending'
        transactions = self._set_initial_contracts()

        charging = charging_engine.ChargingEngine(self._order)
        redirect_url = charging.resolve_charging()

        self.assertEquals(self._paypal_url, redirect_url)

        # Check payment client loading call
        charging_engine.importlib.import_module.assert_called_once_with('wstore.charging_engine.payment_client.payment_client')
        self._payment_class.assert_called_once_with(self._order)
        self._payment_inst.start_redirection_payment.assert_called_once_with(transactions)

        # Check timer call
        charging_engine.threading.Timer.assert_called_once_with(300, charging._timeout_handler)
        self._thread.start.assert_called_once_with()

        # Check payment saving
        self.assertEquals({
            'transactions': transactions,
            'concept': 'initial'
        }, self._order.pending_payment)
        self.assertEquals('pending', self._order.state)
        self._order.save.assert_called_once_with()

    def test_free_charge(self):

        self._set_free_contract()

        charging = charging_engine.ChargingEngine(self._order)
        redirect_url = charging.resolve_charging()

        # Check return value
        self.assertTrue(redirect_url is None)

        # Check invoice generation calls
        charging_engine.InvoiceBuilder.assert_called_once_with(self._order)
        self._invoice_inst.generate_invoice.assert_called_once_with([], 'initial')

        # Check order status
        self.assertEquals('paid', self._order.state)
        self.assertEquals({}, self._order.pending_payment)
        self._order.save.assert_called_once_with()

    def test_invalid_concept(self):

        charging = charging_engine.ChargingEngine(self._order)

        error = None
        try:
            charging.resolve_charging(type_='invalid')
        except ValueError as e:
            error = e

        self.assertFalse(error is None)
        self.assertEquals('Invalid charge type, must be initial, renovation, or use', unicode(e))


BASIC_PAYPAL = {
    'reference': '111111111111111111111111',
    'payerId': 'payer',
    'paymentId': 'payment'
}

MISSING_REF = {
    'payerId': 'payer',
    'paymentId': 'payment'
}

MISSING_PAYER = {
    'reference': '111111111111111111111111',
    'paymentId': 'payment'
}

MISSING_PAYMENT = {
    'reference': '111111111111111111111111',
    'payerId': 'payer'
}

MISSING_RESP = {
    'result': 'error',
    'message': 'The payment has been canceled: Missing required field. It must contain reference, paymentId, and payerId'
}

LOCK_CLOSED_RESP = {
    'result': 'error',
    'message': 'The payment has been canceled: The timeout set to process the payment has finished'
}


class PayPalConfirmationTestCase(TestCase):

    tags = ('ordering', 'paypal-conf')

    def setUp(self):
        # Mock Authentication decorator
        wstore.store_commons.utils.http.authentication_required = decorator_mock
        reload(views)

        # Create a Mock user
        self.user = MagicMock()
        org = MagicMock()
        self.user.userprofile.current_organization = org

        # Create request factory
        self.factory = RequestFactory()

        # Mock ordering client
        self._ordering_inst = MagicMock()
        views.OrderingClient = MagicMock()
        views.OrderingClient.return_value = self._ordering_inst

        # Mock database connection
        views.get_database_connection = MagicMock()
        self._connection_inst = MagicMock()
        self._connection_inst.wstore_order.find_one_and_update.return_value = {
            '_lock': False
        }
        views.get_database_connection.return_value = self._connection_inst

        # Mock Order
        views.Order = MagicMock()
        self._order_inst = MagicMock()
        self._order_inst.order_id = '1'
        self._order_inst.owner_organization = org
        self._order_inst.state = 'pending'
        self._order_inst.pending_payment = {
            'transactions': [],
            'concept': 'initial'
        }
        views.Order.objects.filter.return_value = [self._order_inst]
        views.Order.objects.get.return_value = self._order_inst

        # Mock payment client
        mock_payment_client(self, views)

        # Mock Charging engine
        views.ChargingEngine = MagicMock()
        self._charging_inst = MagicMock()
        views.ChargingEngine.return_value = self._charging_inst

    def tearDown(self):
        reload(wstore.store_commons.utils.http)
        reload(views)

    def _accounting_included(self):
        self._order_inst.pending_payment = {
            'transactions': [],
            'concept': 'initial',
            'accounting': []
        }

    def _invalid_ref(self):
        views.Order.objects.filter.return_value = []

    def _lock_closed(self):
        self._connection_inst.wstore_order.find_one_and_update.return_value = {
            '_lock': True
        }

    def _timeout(self):
        self._order_inst.state = 'paid'

    def _unauthorized(self):
        self.user.userprofile.current_organization = MagicMock()

    def _exception(self):
        self._charging_inst.end_charging.side_effect = Exception('Unexpected')

    @parameterized.expand([
        ('basic', BASIC_PAYPAL, {
            'result': 'correct',
            'message': 'Ok'
        }),
        ('accounting', BASIC_PAYPAL, {
            'result': 'correct',
            'message': 'Ok'
        }, _accounting_included, []),
        ('missing_ref', MISSING_REF, MISSING_RESP, None, None, True),
        ('missing_payerid', MISSING_PAYER, MISSING_RESP, None, None, True),
        ('missing_payment_id', MISSING_PAYMENT, MISSING_RESP, None, None, True),
        ('invalid_ref', BASIC_PAYPAL, {
            'result': 'error',
            'message': 'The payment has been canceled: The provided reference does not identify a valid order'
        }, _invalid_ref, None, True),
        ('lock_closed', BASIC_PAYPAL, LOCK_CLOSED_RESP, _lock_closed, None, True),
        ('timeout_finished', BASIC_PAYPAL, LOCK_CLOSED_RESP, _timeout, None, True, True),
        ('unauthorized', BASIC_PAYPAL, {
            'result': 'error',
            'message': 'The payment has been canceled: You are not authorized to execute the payment'
        }, _unauthorized, None, True, True),
        ('exception', BASIC_PAYPAL, {
            'result': 'error',
            'message': 'The payment has been canceled'
        }, _exception, None, True, True)
    ])
    @override_settings(PAYMENT_METHOD=None)
    def test_paypal_confirmation(self, name, data, expected_resp, side_effect=None, acc=None, error=False, to_del=False):

        if side_effect is not None:
            side_effect(self)

        # Create request
        request = self.factory.post(
            'charging/api/orderManagement/orders/accept/',
            json.dumps(data),
            content_type='application/json',
            HTTP_ACCEPT='application/json'
        )
        request.user = self.user

        # Build class
        paypal_view = views.PayPalConfirmation(permitted_methods=('POST',))

        response = paypal_view.create(request)

        # Check response
        resp = json.loads(response.content)
        self.assertEquals(expected_resp, resp)

        # Check calls
        views.OrderingClient.assert_called_once_with()

        if not error:
            views.get_database_connection.assert_called_once_with()
            self.assertEquals([
                call({'_id': ObjectId('111111111111111111111111')}, {'$set': {'_lock': True}}),
                call({'_id': ObjectId('111111111111111111111111')}, {'$set': {'_lock': False}})],
                self._connection_inst.wstore_order.find_one_and_update.call_args_list
            )

            views.Order.objects.filter.assert_called_once_with(pk='111111111111111111111111')
            views.Order.objects.get.assert_called_once_with(pk='111111111111111111111111')

            self._payment_class.assert_called_once_with(self._order_inst)
            self._payment_inst.end_redirection_payment.assert_called_once_with('payment', 'payer')

            views.ChargingEngine.assert_called_once_with(self._order_inst)
            self._charging_inst.end_charging.assert_called_once_with([], 'initial', acc)

            self.assertEquals([
                call('1', 'inProgress'),
                call('1', 'Completed')
            ], self._ordering_inst.update_state.call_args_list)

        elif to_del:
            self._ordering_inst.update_state.assert_called_once_with('1', 'Failed')
            self._order_inst.delete.assert_called_once_with()