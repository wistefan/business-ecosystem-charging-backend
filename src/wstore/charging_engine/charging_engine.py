# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2015 CoNWeT Lab., Universidad Politécnica de Madrid

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
from __future__ import unicode_literals

import time
import threading
import importlib
from bson import ObjectId
from datetime import datetime

from django.conf import settings

from wstore.charging_engine.models import Unit
from wstore.charging_engine.price_resolver import PriceResolver
from wstore.charging_engine.charging.cdr_manager import CDRManager
from wstore.charging_engine.invoice_builder import InvoiceBuilder
from wstore.ordering.models import Order
from wstore.ordering.ordering_client import OrderingClient
from wstore.store_commons.database import get_database_connection


class ChargingEngine:

    def __init__(self, order):
        self._order = order
        self._price_resolver = PriceResolver()

    def _timeout_handler(self):

        db = get_database_connection()

        # Uses an atomic operation to get and set the _lock value in the purchase
        # document
        pre_value = db.wstore_order.find_one_and_update(
            {'_id': ObjectId(self._order.pk)},
            {'$set': {'_lock': True}}
        )

        # If _lock not exists or is set to false means that this function has
        # acquired the resource
        if '_lock' not in pre_value or not pre_value['_lock']:

            # Only rollback if the state is pending
            if pre_value['state'] == 'pending':
                # Refresh the purchase
                order = Order.objects.get(pk=self._order.pk)
                ordering_client = OrderingClient()
                ordering_client.update_state(order.order_id, 'Failed')
                order.delete()

            else:
                db.wstore_order.find_one_and_update(
                    {'_id': ObjectId(self._order.pk)},
                    {'$set': {'_lock': False}}
                )

    def _fix_price(self, price):

        return '{0:.2f}'.format(price)

    def _charge_client(self, transactions):

        # Load payment client
        cln_str = settings.PAYMENT_CLIENT
        client_package, client_class = cln_str.rsplit('.', 1)

        payment_client = getattr(importlib.import_module(client_package), client_class)

        # build the payment client
        client = payment_client(self._order)

        client.start_redirection_payment(transactions)
        checkout_url = client.get_checkout_url()

        # Set timeout for PayPal transaction to 5 minutes
        t = threading.Timer(300, self._timeout_handler)
        t.start()

        return checkout_url

    def _calculate_renovation_date(self, unit):

        unit_model = Unit.objects.get(name=unit.lower())

        now = datetime.now()
        # Transform now date into seconds
        now = time.mktime(now.timetuple())

        renovation_date = now + (unit_model.renovation_period * 86400)  # Seconds in a day

        renovation_date = datetime.fromtimestamp(renovation_date)
        return renovation_date

    def _end_initial_charge(self, contract, related_model, accounting=None):
        # If a subscription part has been charged update renovation date
        if 'subscription' in related_model:
            updated_subscriptions = []

            for subs in contract.pricing_model['subscription']:
                up_sub = subs
                # Calculate renovation date
                up_sub['renovation_date'] = self._calculate_renovation_date(subs['unit'])
                updated_subscriptions.append(up_sub)

            contract.pricing_model['subscription'] = updated_subscriptions
            related_model['subscription'] = updated_subscriptions

        # Save offerings in org profile
        self._order.owner_organization.acquired_offerings.append(contract.offering.pk)
        self._order.owner_organization.save()

    def _end_use_charge(self, contract, related_model, accounting=None):
        # Move SDR from pending to applied
        self._order.contract.applied_sdrs.extend(self._order.contract.pending_sdrs)
        self._order.contract.pending_sdrs = []
        related_model['charges'] = accounting['charges']
        related_model['deductions'] = accounting['deductions']

    def end_charging(self, transactions, concept, accounting=None):
        """
        Process the second step of a payment once the customer has approved the charge
        :param transactions: List of transactions applied including the total price and the related model
        :param concept: Concept of the charge, it can be initial, renovation, or use
        :param accounting: Accounting information used to compute the charged for pay-per-use models
        """

        end_processors = {
            'initial': self._end_initial_charge,
            'use': self._end_use_charge
        }

        # Update purchase state
        if self._order.state == 'pending':
            self._order.state = 'paid'
            self._order.save()

        time_stamp = datetime.now()

        self._order.pending_payment = {}

        for transaction in transactions:
            contract = self._order.get_item_contract(transaction['item'])

            # Update contracts
            contract.charges.append({
                'date': time_stamp,
                'cost': transaction['price'],
                'currency': transaction['currency'],
                'concept': concept
            })

            contract.last_charge = time_stamp

            end_processors[concept](contract, transaction['related_model'], accounting)

            # If the customer has been charged create the CDR
            cdr_manager = CDRManager(self._order, contract)
            cdr_manager.generate_cdr(transaction['related_model'], str(time_stamp))

        self._order.save()

        # Generate the invoice
        invoice_builder = InvoiceBuilder(self._order)
        invoice_builder.generate_invoice(transactions, concept)

    def _save_pending_charge(self, transactions, applied_accounting=None):
        pending_payment = {
            'transactions': transactions,
            'concept': self._concept
        }

        # If some accounting has been used include it to be saved
        if applied_accounting:
            pending_payment['accounting'] = applied_accounting

        self._order.pending_payment = pending_payment
        self._order.save()

    def _process_initial_charge(self):
        """
        Resolves initial charges, which can include single payments or the initial payment of a subscription
        :return: The URL where redirecting the customer to approve the charge
        """

        transactions = []
        redirect_url = None

        for contract in self._order.contracts:
            related_model = {}
            # Check if there are price parts different from pay per use
            if 'single_payment' in contract.pricing_model:
                related_model['single_payment'] = contract.pricing_model['single_payment']

            if 'subscription' in contract.pricing_model:
                related_model['subscription'] = contract.pricing_model['subscription']

            if len(related_model):
                # Call the price resolver
                price = self._price_resolver.resolve_price(related_model)
                transactions.append({
                    'price': self._fix_price(price),
                    'description': contract.offering.description,
                    'currency': contract.pricing_model['general_currency'],
                    'related_model': related_model,
                    'item': contract.item_id
                })

        if len(transactions):
            # Make the charge
            redirect_url = self._charge_client(transactions)
            self._save_pending_charge(transactions)
        else:
            # If it is not necessary to charge the customer, the state is set to paid
            self._order.state = 'paid'
            self.end_charging(transactions, self._concept)

        return redirect_url

    def _process_usage(self, related_model, unmodified=None):

        redirect_url = None
        accounting_info = None

        # If pending SDR documents resolve the use charging
        if len(self._order.contract.pending_sdrs) > 0:
            related_model['pay_per_use'] = self._price_model['pay_per_use']
            accounting_info = []
            accounting_info.extend(self._order.contract.pending_sdrs)

        # If deductions have been included resolve the discount
        if 'deductions' in self._price_model and len(self._price_model['deductions']) > 0:
            related_model['deductions'] = self._price_model['deductions']

        price = self._price_resolver.resolve_price(related_model, accounting_info)

        # Check if applied accounting info is needed to finish the purchase
        applied_accounting = None
        if accounting_info is not None:
            applied_accounting = self._price_resolver.get_applied_sdr()

        # Deductions can make the price 0
        if price > 0:
            # If not use made, check expenditure limits and accumulated balance
            if applied_accounting is None:
                self._balance_manager.check_expenditure_limits(price)

            redirect_url = self._charge_client(price)

        if unmodified is not None and len(unmodified) > 0:
            related_model['unmodified'] = unmodified

        if self._order.state == 'paid':
            self.end_charging(price, self._concept, related_model, applied_accounting)
        else:
            self._save_pending_charge(price, related_model, applied_accounting=applied_accounting)

        return price, applied_accounting, redirect_url

    def _process_use_charge(self):
        """
        Resolves usage charges, which includes pay-per-use payments
        :return: The URL where redirecting the customer to approve the charge
        """
        self._order.state = 'pending'
        self._order.save()

        if not len(self._order.contract.pending_sdrs):
            raise ValueError('There is not pending SDRs to process')

        related_model = {}
        price, applied_accounting, redirect_url = self._process_usage(related_model)

        return redirect_url

    def resolve_charging(self, type_='initial'):
        """
        Calculates the charge of a customer depending on the pricing model and the type of charge.
        :param type_: Type of charge, it defines if it is an initial charge, a renovation or a usage based charge
        :return: The URL where redirecting the user to be charged (PayPal)
        """

        self._concept = type_

        charging_processors = {
            'initial': self._process_initial_charge,
            'use': self._process_use_charge
        }

        if type_ not in charging_processors:
            raise ValueError('Invalid charge type, must be initial, renovation, or use')

        return charging_processors[type_]()
