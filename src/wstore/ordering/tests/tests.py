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
from copy import deepcopy
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured

from nose_parameterized import parameterized
from mock import MagicMock, call

from django.test import TestCase
from wstore.models import Organization
from wstore.ordering.errors import OrderingError
from wstore.ordering.models import Order, Offering, Contract

from wstore.ordering.tests.test_data import *
from wstore.ordering import ordering_client, ordering_management


class OrderingManagementTestCase(TestCase):

    tags = ('ordering', 'order-manager')

    def setUp(self):
        self._customer = MagicMock()

        # Mock order model
        ordering_management.Order = MagicMock()
        self._order_inst = MagicMock()
        ordering_management.Order.objects.create.return_value = self._order_inst

        # Mock Offering model
        ordering_management.Offering = MagicMock()
        self._offering_inst = MagicMock()
        ordering_management.Offering.objects.filter.return_value = []
        ordering_management.Offering.objects.create.return_value = self._offering_inst

        # Mock Contract model
        ordering_management.Contract = MagicMock()
        self._contract_inst = MagicMock()
        ordering_management.Contract.return_value = self._contract_inst

        # Mock Charging Engine
        ordering_management.ChargingEngine = MagicMock()
        self._charging_inst = MagicMock()
        self._charging_inst.resolve_charging.return_value = 'http://redirectionurl.com/'
        ordering_management.ChargingEngine.return_value = self._charging_inst

        # Mock requests
        ordering_management.requests = MagicMock()
        self._response = MagicMock()
        self._response.status_code = 200
        self._response.json.return_value = OFFERING_PRODUCT
        ordering_management.requests.get.return_value = self._response

        # Mock organization model
        self._org_inst = MagicMock()
        ordering_management.Organization = MagicMock()
        ordering_management.Organization.objects.get.return_value = self._org_inst

        # Mock Product validator
        self._validator_inst = MagicMock()
        ordering_management.ProductValidator = MagicMock()
        ordering_management.ProductValidator.return_value = self._validator_inst
        self._validator_inst.parse_characteristics.return_value = ('type', 'media_type', 'http://location.com')

        # Mock Resource
        self._asset_instance = MagicMock()
        ordering_management.Resource = MagicMock()
        ordering_management.Resource.objects.get.return_value = self._asset_instance

    def _check_offering_call(self, asset, description="Example offering description", is_digital=True):
        ordering_management.Offering.objects.filter.assert_called_once_with(off_id="5")
        ordering_management.Offering.objects.create.assert_called_once_with(
            off_id="5",
            href="http://localhost:8004/DSProductCatalog/api/catalogManagement/v2/productOffering/20:(2.0)",
            owner_organization=self._org_inst,
            name="Example offering",
            description=description,
            version="1.0",
            is_digital=is_digital,
            asset=asset
        )

    def _check_contract_call(self, pricing, revenue_class):
        ordering_management.Contract.assert_called_once_with(
            item_id="1",
            pricing_model=pricing,
            revenue_class=revenue_class,
            offering=self._offering_inst
        )

    def _check_offering_retrieving_call(self):
        ordering_management.Offering.objects.filter.assert_called_once_with(off_id="5")
        ordering_management.Offering.objects.get.assert_called_once_with(off_id="5")
        self.assertEquals('Example offering description', self._offering_inst.description)
        self.assertEquals('1.0', self._offering_inst.version)
        self.assertEquals('http://localhost:8004/DSProductCatalog/api/catalogManagement/v2/productOffering/20:(2.0)', self._offering_inst.href)
        self._offering_inst.save.assert_called_once_with()

    def _basic_add_checker(self):
        # Check offering creation
        self._check_offering_call(self._asset_instance)

        # Check contract creation
        self._check_contract_call({
            'general_currency': 'EUR',
            'single_payment': [{
                'value': '12.00',
                'unit': 'one time',
                'tax_rate': '20.00',
                'duty_free': '10.00'
            }]
        }, "single-payment")
        ordering_management.Organization.objects.get.assert_called_once_with(name='test_user')

    def _non_digital_add_checker(self):
        self._check_offering_call(None, is_digital=False)

    def _recurring_add_checker(self):
        # Check offering creation
        self._check_offering_retrieving_call()

        self._check_contract_call({
            'general_currency': 'EUR',
            'subscription': [{
                'value': '12.00',
                'unit': 'monthly',
                'tax_rate': '20.00',
                'duty_free': '10.00'
            }]
        }, 'subscription')

    def _usage_add_checker(self):
        self._check_offering_call(self._asset_instance, description="")

        self._check_contract_call({
            'general_currency': 'EUR',
            'pay_per_use': [{
                'value': '12.00',
                'unit': 'megabyte',
                'tax_rate': '20.00',
                'duty_free': '10.00'
            }]
        }, 'use')
        ordering_management.Organization.objects.get.assert_called_once_with(name='test_user')

    def _free_add_checker(self):
        self._check_offering_call(self._asset_instance)

        self._check_contract_call({}, None)

    def _non_digital_offering(self):
        self._validator_inst.parse_characteristics.return_value = (None, None, None)

    def _existing_offering(self):
        ordering_management.Offering.objects.filter.return_value = [self._offering_inst]
        ordering_management.Offering.objects.get.return_value = self._offering_inst

    def _no_offering_description(self):
        new_off = deepcopy(OFFERING_PRODUCT)
        del(new_off['description'])
        self._response.json.return_value = new_off

    def _missing_offering(self):
        self._response.status_code = 404

    def _missing_product(self):
        def get(url):
            result = self._response
            if url == "http://producturl.com/":
                result = MagicMock()
                result.status_code = 404
            return result

        ordering_management.requests.get = get

    def _no_parties(self):
        new_off = deepcopy(OFFERING_PRODUCT)
        new_off["relatedParty"] = []
        self._response.json.return_value = new_off

    def _inv_parties(self):
        new_off = deepcopy(OFFERING_PRODUCT)
        new_off["relatedParty"] = [{
            "id": "test_user2",
            "role": "Partner"
        }]
        self._response.json.return_value = new_off

    def _already_owned(self):
        self._existing_offering()
        self._offering_inst.pk = '11111'
        self._customer.current_organization.acquired_offerings = ['11111']

    @parameterized.expand([
        ('basic_add', BASIC_ORDER, _basic_add_checker),
        ('non_digital_add', BASIC_ORDER, _non_digital_add_checker, _non_digital_offering),
        ('recurring_add', RECURRING_ORDER, _recurring_add_checker, _existing_offering),
        ('usage_add', USAGE_ORDER, _usage_add_checker, _no_offering_description),
        ('free_add', FREE_ORDER, _free_add_checker),
        ('no_product_add', NOPRODUCT_ORDER, _free_add_checker),
        ('invalid_initial_state', INVALID_STATE_ORDER, None, None, 'OrderingError: Only acknowledged orders can be initially processed'),
        ('invalid_model', INVALID_MODEL_ORDER, None, None, 'OrderingError: Invalid price model Invalid'),
        ('invalid_offering', BASIC_ORDER, None, _missing_offering, 'OrderingError: The product offering specified in order item 1 does not exists'),
        ('invalid_product', BASIC_ORDER, None, _missing_product, 'OrderingError: The product specification specified in order item 1 does not exists'),
        ('no_parties', BASIC_ORDER, None, _no_parties, 'OrderingError: The product specification included in the order item 1 does not contain a valid provider'),
        ('invalid_party', BASIC_ORDER, None, _inv_parties, 'OrderingError: The product specification included in the order item 1 does not contain a valid provider'),
        ('already_owned', BASIC_ORDER, None, _already_owned, 'OrderingError: The customer already owns the digital product offering Example offering with id 5')
    ])
    def test_process_order(self, name, order, checker, side_effect=None, err_msg=None):

        if side_effect is not None:
            side_effect(self)

        ordering_manager = ordering_management.OrderingManager()
        error = None
        try:
            redirect_url = ordering_manager.process_order(self._customer, order)
        except OrderingError as e:
            error = e

        if err_msg is None:
            self.assertTrue(error is None)

            # Check returned value
            self.assertEquals('http://redirectionurl.com/', redirect_url)

            # Check common calls
            ordering_management.ChargingEngine.assert_called_once_with(self._order_inst)

            # Check offering and product downloads
            self.assertEquals(2, ordering_management.requests.get.call_count)
            self.assertEquals([
                call('http://localhost:8004/DSProductCatalog/api/catalogManagement/v2/productOffering/20:(2.0)'),
                call('http://producturl.com/')
            ], ordering_management.requests.get.call_args_list)

            ordering_management.Order.objects.create.assert_called_once_with(
                order_id="12",
                customer=self._customer,
                owner_organization=self._customer.current_organization,
                state='pending',
                tax_address=self._customer.userprofile.tax_address,
                contracts=[self._contract_inst],
                description=""
            )

            # Check particular calls
            checker(self)
        else:
            self.assertEquals(err_msg, unicode(error))


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


class OrderTestCase(TestCase):

    tags = ('ordering', )

    def setUp(self):
        # Build users and organizations
        customer = User.objects.create_user('test_user')

        owner_org = Organization.objects.create(name='test_org')

        # Build offerings and contracts
        offering1 = Offering(
            off_id='1',
            owner_organization=owner_org,
            name='Offering1',
            version='1.0',
            description='Offering1'
        )

        offering2 = Offering(
            off_id='2',
            owner_organization=owner_org,
            name='Offering2',
            version='1.0',
            description='Offering2'
        )

        self._contract1 = Contract(
            item_id='1',
            offering=offering1,
        )

        self._contract2 = Contract(
            item_id='2',
            offering=offering2,
        )

        # Build order
        self._order = Order.objects.create(
            description='',
            order_id='1',
            customer=customer,
            state='pending',
            contracts=[self._contract1, self._contract2]
        )

    def test_get_item_contract(self):
        contract = self._order.get_item_contract('2')
        self.assertEquals(self._contract2, contract)

    def test_get_item_contract_invalid(self):
        error = None
        try:
            self._order.get_item_contract('3')
        except OrderingError as e:
            error = e

        self.assertFalse(error is None)
        self.assertEquals('OrderingError: Invalid item id', unicode(e))

