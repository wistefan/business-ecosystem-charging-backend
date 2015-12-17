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

import requests

from wstore.models import Organization
from wstore.store_commons.rollback import rollback
from wstore.charging_engine.charging_engine import ChargingEngine
from wstore.ordering.errors import OrderingError
from wstore.ordering.models import Order, Contract, Offering


class OrderingManager:

    def __init__(self):
        pass

    def _get_offering(self, item):
        offering_url = item['productOffering']['href']

        r = requests.get(offering_url)

        if r.status_code != 200:
            raise OrderingError('The product offering specified in order item ' + item['id'] + ' does not exists')

        offering_info = r.json()
        offering_id = offering_info['id']

        # Check if the offering contains a description
        description = ''
        if 'description' in offering_info:
            description = offering_info['description']

        # Check if the offering has been already loaded in the system
        if len(Offering.objects.filter(off_id=offering_id)) > 0:
            offering = Offering.objects.get(off_id=offering_id)

            offering.description = description

            offering.version = offering_info['version']
            offering.href = offering_url
            offering.save()
        else:
            # Download product specification to obtain related parties
            product_url = offering_info['productSpecification']['href']
            r1 = requests.get(product_url)

            if r1.status_code != 200:
                raise OrderingError('The product specification specified in order item ' + item['id'] + ' does not exists')

            product_info = r1.json()

            # Get offering provider (Owner role)
            for party in product_info['relatedParty']:
                if party['role'].lower() == 'owner':
                    provider = Organization.objects.get(name=party['id'])
                    break
            else:
                raise OrderingError('The product specification included in the order item ' + item['id'] + ' does not contain a valid provider')

            offering = Offering.objects.create(
                off_id=offering_id,
                href=offering_url,
                owner_organization=provider,
                name=offering_info['name'],
                description=description,
                version=offering_info['version']
            )

        return offering

    def _build_contract(self, item):
        # TODO: Check that the ordering API is actually validating that the chosen pricing and characteristics are valid for the given product

        # Build pricing if included
        pricing = {}
        if 'product' in item and 'productPrice' in item['product'] and len(item['product']['productPrice']):
            price = item['product']['productPrice'][0]

            model_mapper = {
                'one time': 'single_payment',
                'recurring': 'subscription',
                'usage': 'pay_per_use'
            }

            if price['priceType'].lower() not in model_mapper:
                raise OrderingError('Invalid price model ' + price['priceType'])

            pricing['general_currency'] = price['price']['currencyCode']
            unit_field = {
                'usage': 'unitOfMeasure',
                'recurring': 'recurringChargePeriod',
                'one time': 'priceType'
            }

            price_unit = {
                'value': price['price']['taxIncludedAmount'],
                'unit': price[unit_field[price['priceType'].lower()]].lower(),
                'tax_rate': price['price']['taxRate'],
                'duty_free': price['price']['dutyFreeAmount']
            }

            pricing[model_mapper[price['priceType'].lower()]] = [price_unit]

        # Calculate the revenue sharing class
        revenue_class = None
        if 'pay_per_use' in pricing:
            revenue_class = 'use'
        elif 'subscription' in pricing:
            revenue_class = 'subscription'
        elif 'single_payment' in pricing:
            revenue_class = 'single-payment'

        return Contract(
            item_id=item['id'],
            pricing_model=pricing,
            revenue_class=revenue_class,
            offering=self._get_offering(item)
        )

    def _process_add_items(self, user, items, order_id, description):
        # TODO: Check that for digital product the offering is not already owned

        new_contracts = []
        for item in items:
            new_contracts.append(self._build_contract(item))

        order = Order.objects.create(
            order_id=order_id,
            customer=user,
            owner_organization=user.current_organization,
            state='pending',
            tax_address=user.userprofile.tax_address,
            contracts=new_contracts,
            description=description
        )

        self.rollback_logger['models'].append(order)

        charging_engine = ChargingEngine(order)
        return charging_engine.resolve_charging()

    def _process_modify_items(self, user, items):
        pass

    def _process_delete_items(self, user, items):
        pass

    @rollback()
    def process_order(self, customer, order):

        # Check initial state of the order. It must be Acknowledged
        if order['state'].lower() != 'acknowledged':
            raise OrderingError('Only acknowledged orders can be initially processed')

        # Classify order items by action
        items = {
            'add': [],
            'modify': [],
            'delete': [],
            'no_change': []
        }
        for item in order['orderItem']:
            items[item['action'].lower()].append(item)

        # Process order items separately depending on its action. no_change items are not processed
        if len(items['modify']):
            self._process_modify_items(customer, items['modify'])

        if len(items['delete']):
            self._process_delete_items(customer, items['delete'])

        # The processing of add items can generate a redirection URL
        redirection_url = None
        if len(items['add']):

            description = ''
            if 'description' in order:
                description = order['description']

            redirection_url = self._process_add_items(customer, items['add'], order['id'], description)

        return redirection_url
