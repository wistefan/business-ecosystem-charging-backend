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

import json
from django.http import HttpResponse
from wstore.ordering.errors import OrderingError

from wstore.ordering.ordering_management import OrderingManager
from wstore.ordering.ordering_client import OrderingClient
from wstore.store_commons.resource import Resource
from wstore.store_commons.utils.http import build_response, supported_request_mime_types, authentication_required


class OrderingCollection(Resource):

    @authentication_required
    @supported_request_mime_types(('application/json',))
    def create(self, request):
        """
        Receives notifications from the ordering API when a new order is created
        :param request:
        :return:
        """

        user = request.user
        try:
            order = json.loads(request.body)
        except:
            return build_response(request, 400, 'The provided data is not a valid JSON object')

        # Check that the user has a billing address
        response = None
        if 'street' not in user.userprofile.current_organization.tax_address:
            response = build_response(request, 400, 'The customer has not defined a billing address')

        try:
            om = OrderingManager()
            redirect_url = om.process_order(user, order)
        except Exception as e:

            err_msg = 'Your order could not be processed'
            if isinstance(e, OrderingError):
                err_msg = unicode(e)

            response = build_response(request, 400, err_msg)

        if response is not None:
            client = OrderingClient()
            client.update_state(order['id'], 'InProgress')
            client.update_state(order['id'], 'Failed')

        elif redirect_url is not None:
            response = HttpResponse(json.dumps({
                'redirectUrl': redirect_url
            }), status=200, mimetype='application/json; charset=utf-8')

        else:
            response = build_response(request, 200, 'OK')

        return response
