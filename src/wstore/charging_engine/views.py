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
from django.core.exceptions import PermissionDenied

import json
import importlib
from bson import ObjectId
from datetime import datetime

from django.conf import settings
from django.http import HttpResponse

from wstore.ordering.inventory_client import InventoryClient
from wstore.ordering.ordering_client import OrderingClient
from wstore.store_commons.resource import Resource
from wstore.store_commons.utils.http import build_response, supported_request_mime_types, authentication_required
from wstore.ordering.models import Order
from wstore.ordering.errors import PaymentError
from wstore.charging_engine.charging_engine import ChargingEngine
from wstore.charging_engine.accounting.sdr_manager import SDRManager
from wstore.store_commons.database import get_database_connection


class ServiceRecordCollection(Resource):

    def _get_datetime(self, time):
        try:
            time_stamp = datetime.strptime(time, '%Y-%m-%dT%H:%M:%S.%f')
        except:
            time_stamp = datetime.strptime(time, '%Y-%m-%d %H:%M:%S.%f')

        return time_stamp

    # This method is used to load SDR documents and
    # start the charging process
    @supported_request_mime_types(('application/json',))
    @authentication_required
    def create(self, request):
        try:
            # Extract SDR document from the HTTP request
            data = json.loads(request.body)
        except:
            return build_response(request, 400, 'The request does not contain a valid JSON object')

        # Validate SDR structure
        if 'orderId' not in data or 'productId' not in data or 'customer' not in data or 'correlationNumber' not in data\
                or 'recordType' not in data or 'unit' not in data or 'value' not in data or 'timestamp' not in data:

            msg = 'Missing required field, it must contain: orderId, productId, customer, '
            msg += 'correlationNumber, timestamp, recordType, unit, and value'
            return build_response(request, 400, msg)

        # Get the order
        try:
            order = Order.objects.get(order_id=data['orderId'])
        except:
            return build_response(request, 404, 'Invalid orderId, the order does not exists')

        try:
            contract = order.get_product_contract(data['productId'])
        except:
            return build_response(request, 404, 'Invalid productId, the contract does not exist')

        # Include the new SDR
        try:
            sdr_manager = SDRManager(request.user, order, contract)
            sdr_manager.include_sdr(data)
        except PermissionDenied as e:
            return build_response(request, 403, unicode(e))
        except ValueError as e:
            return build_response(request, 400, unicode(e))
        except:
            return build_response(request, 500, 'The SDR document could not be processed due to an unexpected error')

        return build_response(request, 200, 'OK')

    @authentication_required
    def read(self, request, reference):
        # Check reference
        try:
            purchase = Order.objects.get(ref=reference)
        except:
            return build_response(request, 404, 'There is not any purchase with reference ' + reference)

        # Check permissions
        user = request.user

        if not request.user.is_staff and \
                user.userprofile.current_organization != purchase.owner_organization:
            return build_response(request, 403, 'You are not authorized to read accounting info of the given purchase')

        # Check if a contract has been created for the given purchase
        try:
            contract = purchase.contract
        except:
            return HttpResponse(json.dumps([]), status=200, mimetype="application/json")

        if contract is None:
            return HttpResponse(json.dumps([]), status=200, mimetype="application/json")

        # Get parameters
        from_ = request.GET.get('from', None)
        to = request.GET.get('to', None)
        label = request.GET.get('label', None)

        # Check from and to formats
        if from_ is not None:
            try:
                from_ = self._get_datetime(from_)
            except:
                return build_response(request, 400, 'Invalid "from" parameter, must be a datetime')

        if to is not None:
            try:
                to = self._get_datetime(to)
            except:
                return build_response(request, 400, 'Invalid "to" parameter, must be a datetime')

        # Build response
        response = []
        sdrs = []
        sdrs.extend(contract.applied_sdrs)
        sdrs.extend(contract.pending_sdrs)

        for sdr in sdrs:
            if from_ is not None and from_ > sdr['time_stamp']:
                continue

            if to is not None and to < sdr['time_stamp']:
                break

            if label is not None and sdr['component_label'].lower() != label.lower():
                continue

            sdr['time_stamp'] = unicode(sdr['time_stamp'])
            response.append(sdr)

        return HttpResponse(json.dumps(response), status=200, mimetype="application/json")


class PayPalConfirmation(Resource):

    def _set_initial_states(self, transactions, raw_order, order):
        # Set all order items as in progress
        self.ordering_client.update_state(raw_order, 'InProgress')

        # Set order items of digital products as completed
        involved_items = [t['item'] for t in transactions]

        digital_items = []
        for item in raw_order['orderItem']:
            if item['id'] in involved_items and order.get_item_contract(item['id']).offering.is_digital:
                digital_items.append(item)

        self.ordering_client.update_state(raw_order, 'Completed', digital_items)

    def _set_renovation_states(self, transactions, raw_order, order):
        inventory_client = InventoryClient()

        for transaction in transactions:
            contract = order.get_item_contract(transaction['item'])
            inventory_client.activate_product(contract.product_id)

    # This method is used to receive the PayPal confirmation
    # when the customer is paying using his PayPal account
    @supported_request_mime_types(('application/json',))
    @authentication_required
    def create(self, request):

        order = None
        concept = None
        self.ordering_client = OrderingClient()
        try:
            # Extract payment information
            data = json.loads(request.body)

            if 'reference' not in data or 'paymentId' not in data or 'payerId' not in data:
                raise ValueError('Missing required field. It must contain reference, paymentId, and payerId')

            reference = data['reference']
            token = data['paymentId']
            payer_id = data['payerId']

            if not Order.objects.filter(pk=reference):
                raise ValueError('The provided reference does not identify a valid order')

            db = get_database_connection()

            # Uses an atomic operation to get and set the _lock value in the purchase
            # document
            pre_value = db.wstore_order.find_one_and_update(
                {'_id': ObjectId(reference)},
                {'$set': {'_lock': True}}
            )

            # If the value of _lock before setting it to true was true, means
            # that the time out function has acquired it previously so the
            # view ends
            if not pre_value or '_lock' in pre_value and pre_value['_lock']:
                raise PaymentError('The timeout set to process the payment has finished')

            order = Order.objects.get(pk=reference)
            raw_order = self.ordering_client.get_order(order.order_id)
            pending_info = order.pending_payment
            concept = pending_info['concept']

            # Check that the request user is authorized to end the payment
            if request.user.userprofile.current_organization != order.owner_organization:
                raise PaymentError('You are not authorized to execute the payment')

            # If the purchase state value is different from pending means that
            # the timeout function has completely ended before acquire the resource
            # so _lock is set to false and the view ends
            if order.state != 'pending':
                db.wstore_order.find_one_and_update(
                    {'_id': ObjectId(reference)},
                    {'$set': {'_lock': False}}
                )
                raise PaymentError('The timeout set to process the payment has finished')

            transactions = pending_info['transactions']

            # Get the payment client
            # Load payment client
            cln_str = settings.PAYMENT_CLIENT
            client_package, client_class = cln_str.rsplit('.', 1)

            payment_client = getattr(importlib.import_module(client_package), client_class)

            # build the payment client
            client = payment_client(order)
            client.end_redirection_payment(token, payer_id)

            charging_engine = ChargingEngine(order)
            accounting = None
            if 'accounting' in pending_info:
                accounting = pending_info['accounting']

            charging_engine.end_charging(transactions, concept, accounting)
        except Exception as e:

            # Rollback the purchase if existing
            if order is not None and raw_order is not None and concept == 'initial':
                # Set the order to failed in the ordering API
                self.ordering_client.update_state(raw_order, 'InProgress')
                self.ordering_client.update_state(raw_order, 'Failed')
                order.delete()

            expl = ' due to an unexpected error'
            err_code = 500
            if isinstance(e, PaymentError) or isinstance(e, ValueError):
                expl = ': ' + unicode(e)
                err_code = 403

            msg = 'The payment has been canceled' + expl
            return build_response(request, err_code, msg)

        # Change states of TMForum resources (orderItems, products, etc)
        # depending on the concept of the payment

        states_processors = {
            'initial': self._set_initial_states,
            'renovation': self._set_renovation_states
        }
        states_processors[concept](transactions, raw_order, order)

        # _lock is set to false
        db.wstore_order.find_one_and_update(
            {'_id': ObjectId(reference)},
            {'$set': {'_lock': False}}
        )

        return build_response(request, 200, 'Ok')


class PayPalCancellation(Resource):

    # This method is used when the user cancel a charge
    # when is using a PayPal account
    @supported_request_mime_types(('application/json', ))
    @authentication_required
    def create(self, request):
        # In case the user cancels the payment is necessary to update
        # the database in order to avoid an inconsistent state
        try:
            data = json.loads(request.body)
            order = Order.objects.get(pk=data['reference'])

            client = OrderingClient()
            raw_order = client.get_order(order.order_id)

            # Set the order to failed in the ordering API
            client.update_state(raw_order, 'Failed')

            order.delete()
        except:
            return build_response(request, 400, 'Invalid request')

        return build_response(request, 200, 'Ok')
