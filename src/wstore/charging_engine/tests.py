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
from wstore.ordering.errors import OrderingError
import wstore.store_commons.utils.http
from bson.objectid import ObjectId
from datetime import datetime

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
        self._order.owner_organization.acquired_offerings = []

        charging_engine.Unit = MagicMock()
        unit = MagicMock()
        unit.renovation_period = 30
        charging_engine.Unit.objects.get.return_value = unit

        # Mock payment client
        mock_payment_client(self, charging_engine)
        self._payment_inst.get_checkout_url.return_value = self._paypal_url

        # Mock threading
        charging_engine.threading = MagicMock()

        self._thread = MagicMock()
        charging_engine.threading.Timer.return_value = self._thread

        # Mock invoice builder
        charging_engine.InvoiceBuilder = MagicMock()

        # Mock CDR Manager
        charging_engine.CDRManager = MagicMock()

        # Mock datetime
        now = datetime(2016, 1, 20, 13, 12, 39)
        charging_engine.datetime = MagicMock()
        charging_engine.datetime.now.return_value = now
        charging_engine.datetime.fromtimestamp.return_value = datetime(2016, 1, 26, 13, 12, 39)

        charging_engine.NotificationsHandler = MagicMock()
        charging_engine.settings.PAYMENT_CLIENT = 'wstore.charging_engine.payment_client.payment_client.PaymentClient'

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

    def _get_subscription(self, renovation_date=None):
        pricing = {
            'general_currency': 'EUR',
            'subscription': [{
                'value': '12.00',
                'unit': 'monthly',
                'tax_rate': '20.00',
                'duty_free': '10.00'
            }]
        }

        if renovation_date is not None:
            pricing['subscription'][0]['renovation_date'] = renovation_date

        return pricing

    def _mock_contract(self, info):
        contract = MagicMock()
        contract.offering.description = info['description']
        contract.offering.pk = info['offering_pk']
        contract.item_id = info['item_id']
        contract.charges = []
        contract.pricing_model = info['pricing']
        return contract

    def _set_initial_contracts(self):
        contract1 = self._mock_contract({
            'description': 'Offering 1 description',
            'offering_pk': '111111',
            'item_id': '1',
            'pricing': self._get_single_payment()
        })
        contract2 = self._mock_contract({
            'description': 'Offering 2 description',
            'offering_pk': '222222',
            'item_id': '2',
            'pricing': self._get_subscription()
        })

        self._order.contracts = [contract1, contract2]
        # Mock get contracts
        self._order.get_item_contract.side_effect = self._order.contracts

        return [{
            'price': '12.00',
            'duty_free': '10.00',
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
            'duty_free': '10.00',
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

    def _set_renovation_contracts(self):
        contract1 = self._mock_contract({
            'description': 'Offering 1 description',
            'offering_pk': '111111',
            'item_id': '1',
            'pricing': self._get_single_payment()
        })
        contract2 = self._mock_contract({
            'description': 'Offering 2 description',
            'offering_pk': '222222',
            'item_id': '2',
            'pricing': self._get_subscription(datetime(2015, 10, 01, 10, 10))
        })
        contract3 = self._mock_contract({
            'description': 'Offering 3 description',
            'offering_pk': '333333',
            'item_id': '3',
            'pricing': self._get_subscription(datetime.now())
        })

        self._order.contracts = [contract1, contract2, contract3]
        # Mock get contracts
        self._order.get_item_contract.side_effect = [contract2]

        return [{
            'price': '12.00',
            'duty_free': '10.00',
            'description': 'Offering 2 description',
            'currency': 'EUR',
            'related_model': {
                'subscription': [{
                    'value': '12.00',
                    'unit': 'monthly',
                    'tax_rate': '20.00',
                    'duty_free': '10.00',
                    'renovation_date': datetime(2015, 10, 01, 10, 10)
                }]
            },
            'item': '2'
        }]

    def _set_subscription_contract(self):
        self._order.contracts = [
            self._mock_contract({
                'description': 'Offering 3 description',
                'offering_pk': '333333',
                'item_id': '3',
                'pricing': self._get_subscription(datetime.now())
            })
        ]
        return []

    def _set_free_contract(self):
        contract = MagicMock()
        contract.offering.description = 'Offering description'
        contract.item_id = '1'
        contract.pricing_model = {}

        self._order.contracts = [contract]

    @parameterized.expand([
        ('initial', _set_initial_contracts),
        ('renovation', _set_renovation_contracts)
    ])
    def test_payment(self, name, contract_gen):

        self._order.state = 'pending'
        transactions = contract_gen(self)

        charging = charging_engine.ChargingEngine(self._order)
        redirect_url = charging.resolve_charging(name)

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
            'concept': name
        }, self._order.pending_payment)
        self.assertEquals('pending', self._order.state)
        self._order.save.assert_called_once_with()

    def test_renovation_error(self):
        self._order.state = 'pending'
        self._set_subscription_contract()

        charging = charging_engine.ChargingEngine(self._order)

        error = None
        try:
            charging.resolve_charging('renovation')
        except OrderingError as e:
            error = e

        self.assertTrue(error is not None)
        self.assertEquals('OrderingError: There is not recurring payments to renovate', unicode(error))

    def test_free_charge(self):

        self._set_free_contract()

        charging = charging_engine.ChargingEngine(self._order)
        redirect_url = charging.resolve_charging()

        # Check return value
        self.assertTrue(redirect_url is None)

        # Check invoice generation calls
        charging_engine.InvoiceBuilder.assert_called_once_with(self._order)
        charging_engine.InvoiceBuilder().generate_invoice.assert_called_once_with([], 'initial')

        # Check order status
        self.assertEquals('paid', self._order.state)
        self.assertEquals({}, self._order.pending_payment)
        self._order.save.assert_called_once_with()

    def _validate_end_initial_payment(self, transactions):
        self.assertEquals([
            call('1'),
            call('2')
        ], self._order.get_item_contract.call_args_list)

        self.assertEquals(['111111', '222222'], self._order.owner_organization.acquired_offerings)
        self.assertEquals([
            call(),
            call()
        ], self._order.owner_organization.save.call_args_list)

        self.assertEquals([
            call(self._order, self._order.contracts[0]),
            call(self._order, self._order.contracts[1]),
        ], charging_engine.CDRManager.call_args_list)

        self.assertEquals([
            call(transactions[0]['related_model'], '2016-01-20 13:12:39'),
            call(transactions[1]['related_model'], '2016-01-20 13:12:39')
        ], charging_engine.CDRManager().generate_cdr.call_args_list)

        charging_engine.NotificationsHandler.assert_called_once_with()
        charging_engine.NotificationsHandler().send_acquired_notification.assert_called_once_with(self._order)

        self.assertEquals([
            call(self._order, self._order.contracts[0]),
            call(self._order, self._order.contracts[1])
        ], charging_engine.NotificationsHandler().send_provider_notification.call_args_list)

        for cnt in self._order.contracts:
            cnt.save.assert_called_once_with()

        self.assertEquals([{
            'date': datetime(2016, 1, 20, 13, 12, 39),
            'cost': '12.00',
            'currency': 'EUR',
            'concept': 'initial'
        }], self._order.contracts[0].charges)

        self.assertEquals([{
            'date': datetime(2016, 1, 20, 13, 12, 39),
            'cost': '12.00',
            'currency': 'EUR',
            'concept': 'initial'
        }], self._order.contracts[1].charges)

    def _validate_end_renovation_payment(self, transactions):
        self.assertEquals([
            call('2')
        ], self._order.get_item_contract.call_args_list)

        charging_engine.CDRManager.assert_called_once_with(self._order, self._order.contracts[1])

        # No new offering has been included
        self.assertEquals([], self._order.owner_organization.acquired_offerings)
        charging_engine.CDRManager().generate_cdr.assert_called_once_with(transactions[0]['related_model'], '2016-01-20 13:12:39')

        self.assertEquals(0, self._order.contracts[0].call_count)
        self._order.contracts[1].save.assert_called_once_with()
        self.assertEquals(0, self._order.contracts[2].call_count)

        self.assertEquals([], self._order.contracts[0].charges)

        self.assertEquals([{
            'date': datetime(2016, 1, 20, 13, 12, 39),
            'cost': '12.00',
            'currency': 'EUR',
            'concept': 'renovation'
        }], self._order.contracts[1].charges)

        self.assertEquals([], self._order.contracts[2].charges)

    @parameterized.expand([
        ('initial', _set_initial_contracts, _validate_end_initial_payment),
        ('renovation', _set_renovation_contracts, _validate_end_renovation_payment)
    ])
    def test_end_payment(self, name, contract_gen, validator):
        self._order.state = 'pending'
        transactions = contract_gen(self)

        charging = charging_engine.ChargingEngine(self._order)
        charging.end_charging(transactions, name)

        validator(self, transactions)

        # Validate calls
        self.assertEquals('paid', self._order.state)

        charging_engine.Unit.objects.get.assert_called_once_with(name='monthly')

        self.assertEquals({
            'general_currency': 'EUR',
            'subscription': [{
                'value': '12.00',
                'unit': 'monthly',
                'tax_rate': '20.00',
                'duty_free': '10.00',
                'renovation_date': datetime(2016, 1, 26, 13, 12, 39)
            }]
        }, self._order.contracts[1].pricing_model)

        charging_engine.datetime.fromtimestamp.assert_called_once_with(1455909159.0)

        self.assertEquals([
            call(),
            call()
        ], self._order.save.call_args_list)

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
        self._raw_order = {
            'id': '1',
            'orderItem': [{
                'id': '1'
            }, {
                'id': '2'
            }]
        }
        self._ordering_inst.get_order.return_value = self._raw_order

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

        views.settings.PAYMENT_CLIENT = 'wstore.charging_engine.payment_client.payment_client.PaymentClient'

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

    def _non_digital_assets(self):
        offering_mock = MagicMock()
        offering_mock.offering.is_digital = False
        self._order_inst.get_item_contract.return_value = offering_mock

    @parameterized.expand([
        ('basic', BASIC_PAYPAL, {
            'result': 'correct',
            'message': 'Ok'
        }, [{'id': '1'}, {'id': '2'}]),
        ('non_digital', BASIC_PAYPAL, {
            'result': 'correct',
            'message': 'Ok'
        }, [], _non_digital_assets),
        ('accounting', BASIC_PAYPAL, {
            'result': 'correct',
            'message': 'Ok'
        }, [{'id': '1'}, {'id': '2'}], _accounting_included, []),
        ('missing_ref', MISSING_REF, MISSING_RESP, None, None, None, True),
        ('missing_payerid', MISSING_PAYER, MISSING_RESP, None, None, None, True),
        ('missing_payment_id', MISSING_PAYMENT, MISSING_RESP, None, None, None, True),
        ('invalid_ref', BASIC_PAYPAL, {
            'result': 'error',
            'message': 'The payment has been canceled: The provided reference does not identify a valid order'
        }, None, _invalid_ref, None, True),
        ('lock_closed', BASIC_PAYPAL, LOCK_CLOSED_RESP, None, _lock_closed, None, True),
        ('timeout_finished', BASIC_PAYPAL, LOCK_CLOSED_RESP, None, _timeout, None, True, True),
        ('unauthorized', BASIC_PAYPAL, {
            'result': 'error',
            'message': 'The payment has been canceled: You are not authorized to execute the payment'
        }, None, _unauthorized, None, True, True),
        ('exception', BASIC_PAYPAL, {
            'result': 'error',
            'message': 'The payment has been canceled due to an unexpected error'
        }, None, _exception, None, True, True)
    ])
    def test_paypal_confirmation(self, name, data, expected_resp, completed=None, side_effect=None, acc=None, error=False, to_del=False):

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

            self._ordering_inst.get_order.assert_called_once_with('1')

            self.assertEquals([call('1'), call('2')], self._order_inst.get_item_contract.call_args_list)
            self.assertEquals([
                call(self._raw_order, 'InProgress'),
                call(self._raw_order, 'Completed', completed)
            ], self._ordering_inst.update_state.call_args_list)

        elif to_del:
            self.assertEquals([
                call(self._raw_order, 'InProgress'),
                call(self._raw_order, 'Failed')
            ], self._ordering_inst.update_state.call_args_list)
            self._order_inst.delete.assert_called_once_with()
