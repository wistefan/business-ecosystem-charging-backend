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

import os

from django.conf import settings
from django.utils.encoding import smart_str
from django.views.static import serve
from django.http import HttpResponse

from store_commons.utils.http import build_response
from wstore.store_commons.resource import Resource as API_Resource

from wstore.models import Resource
from wstore.ordering.models import Order, Offering


class ServeMedia(API_Resource):

    def read(self, request, path, name):

        dir_path = os.path.join(settings.MEDIA_ROOT, path)

        # Protect the resources from not authorized downloads
        if path.startswith('assets'):
            # Retrieve the given digital asset
            try:
                resource_path = os.path.join(settings.MEDIA_URL, path)
                resource_path = os.path.join(resource_path, name)
                asset = Resource.objects.get(resource_path=resource_path)
            except:
                return build_response(request, 404, 'The specified asset does not exists')

            # Check if the user has permissions to download the asset
            if not asset.is_public:
                if request.user.is_anonymous():
                    return build_response(request, 401, 'You must be authenticated to download the specified asset')

                if request.user.userprofile.current_organization != asset.provider:
                    # Check if the user has acquired the asset
                    for off in request.user.userprofile.current_organization.acquired_offerings:
                        offering = Offering.objects.get(pk=off)
                        if offering.asset == asset:
                            break
                    else:
                        return build_response(request, 403, 'You are not authorized to download the specified asset')

        elif path.startswith('bills'):
            if request.user.is_anonymous():
                return build_response(request, 401, 'You must provide credentials for downloading invoices')

            try:
                order = Order.objects.get(pk=name[:24])
            except:
                return build_response(request, 404, 'The specified invoice does not exists')

            if order.owner_organization != request.user.userprofile.current_organization:
                return build_response(request, 403, 'You are not authorized to download the specified invoice')
        else:
            return build_response(request, 404, 'Resource not found')

        local_path = os.path.join(dir_path, name)

        if not os.path.isfile(local_path):
            return build_response(request, 404, 'Resource not found')

        if not getattr(settings, 'USE_XSENDFILE', False):
            return serve(request, local_path, document_root='/')
        else:
            response = HttpResponse()
            response['X-Sendfile'] = smart_str(local_path)
            return response
