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

from mock import MagicMock

from django.test import TestCase
from django.test.utils import override_settings

from wstore.charging_engine import charging_engine


class ChargingEngineTestCase(TestCase):

    tags = ('ordering', 'charging-engine')
    _paypal_url = 'http://paypalurl.com'

    def setUp(self):
        # Mock order
        self._order = MagicMock()

        # Mock payment client
        charging_engine.importlib = MagicMock()
        module_mock = MagicMock()
        self._payment_class = MagicMock()
        module_mock.PaymentClient = self._payment_class

        self._payment_inst = MagicMock()
        self._payment_inst.get_checkout_url.return_value = self._paypal_url

        self._payment_class.return_value = self._payment_inst
        charging_engine.importlib.import_module.return_value = module_mock

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
