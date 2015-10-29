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

from __future__ import unicode_literals

import json

from django.http import HttpResponse

from wstore.store_commons.resource import Resource
from wstore.store_commons.utils.http import build_response, get_content_type, supported_request_mime_types, \
    authentication_required
from wstore.models import Organization, Resource as OfferingResource
from wstore.asset_manager.resources_management import get_provider_resources, delete_resource,\
    update_resource, upgrade_resource, upload_asset
from wstore.store_commons.errors import ConflictError


class ResourceCollection(Resource):

    # Creates a new resource associated with an user
    @supported_request_mime_types(('application/json', 'multipart/form-data'))
    @authentication_required
    def create(self, request):

        user = request.user
        profile = user.userprofile
        content_type = get_content_type(request)[0]

        if 'provider' in profile.get_current_roles():

            try:
                if content_type == 'application/json':
                    data = json.loads(request.body)
                    upload_asset(user, data)
                else:
                    data = json.loads(request.POST['json'])
                    f = request.FILES['file']
                    upload_asset(user, data, file_=f)

            except ConflictError as e:
                return build_response(request, 409, unicode(e))
            except Exception as e:
                return build_response(request, 400, unicode(e))
        else:
            return build_response(request, 403, "You don't have the provider role")

        return build_response(request, 201, 'Created')

    @authentication_required
    def read(self, request):

        pagination = {
            'start': request.GET.get('start', None),
            'limit': request.GET.get('limit', None)
        }
        if pagination['start'] is None or pagination['limit'] is None:
            pagination = None

        profile = request.user.userprofile

        if 'provider' in profile.get_current_roles():
            try:
                response = get_provider_resources(request.user, pagination=pagination)
            except Exception, e:
                return build_response(request, 400, unicode(e))
        else:
            return build_response(request, 403, 'Forbidden')

        return HttpResponse(json.dumps(response), status=200, mimetype='application/json; charset=utf-8')


def _get_resource(resource_id_info):
    try:
        # Get the resource
        provider_org = Organization.objects.get(name=resource_id_info['provider'])
        resource = OfferingResource.objects.get(provider=provider_org, name=resource_id_info['name'], version=resource_id_info['version'])
    except:
        raise ValueError('Resource not found')

    return resource


def _call_resource_entry_method(request, resource_id_info, method, data, is_del=False):

    response = build_response(request, 200, 'OK')

    if is_del:
        response = build_response(request, 204, 'No Content')

    error = False

    try:
        resource = _get_resource(resource_id_info)
    except:
        error = True
        response = build_response(request, 404, 'Resource not found')

    # Check permissions
    if not error and ('provider' not in request.user.userprofile.get_current_roles() or
            not request.user.userprofile.current_organization == resource.provider):

        error = True
        response = build_response(request, 403, 'Forbidden')

    # Try to make the specified action
    if not error:
        try:
            args = (resource, ) + data
            method(*args)
        except Exception as e:
            response = build_response(request, 400, unicode(e))

    # Return the response
    return response


class ResourceEntry(Resource):

    @authentication_required
    def delete(self, request, provider, name, version):
        return _call_resource_entry_method(request, {
            'provider': provider,
            'name': name,
            'version': version
        }, delete_resource, (request.user, ), True)

    @supported_request_mime_types(('application/json', 'multipart/form-data'))
    @authentication_required
    def create(self, request, provider, name, version):

        content_type = get_content_type(request)[0]

        try:
            # Extract the data depending on the content type
            if content_type == 'application/json':
                data = json.loads(request.body)
                params = (request.user, data, )
            else:
                data = json.loads(request.POST['json'])
                file_ = request.FILES['file']
                params = (request.user, data, file_)
        except:
            return build_response(request, 400, 'Invalid content')

        return _call_resource_entry_method(request, {
            'provider': provider,
            'name': name,
            'version': version
        }, upgrade_resource, params)

    @supported_request_mime_types(('application/json',))
    @authentication_required
    def update(self, request, provider, name, version):

        try:
            # Extract the data depending on the content type
            data = json.loads(request.body)
            params = (request.user, data, )
        except:
            return build_response(request, 400, 'Invalid content')

        return _call_resource_entry_method(request, {
            'provider': provider,
            'name': name,
            'version': version
        }, update_resource, params)
