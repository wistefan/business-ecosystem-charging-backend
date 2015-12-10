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
from wstore.models import UserProfile, Organization
from wstore.models import Resource


class ServeMedia(API_Resource):

    def read(self, request, path, name):
        if request.method != 'GET':
            return build_response(request, 415, 'Method not supported')

        dir_path = os.path.join(settings.MEDIA_ROOT, path)

        # Protect the resources from not authorized downloads
        if dir_path.endswith('resources'):
            if request.user.is_anonymous():
                return build_response(request, 401, 'Unauthorized')

            # Check if the request user has access to the resource
            splited_name = name.split('__')
            prov = Organization.objects.get(name=splited_name[0])
            resource = Resource.objects.get(provider=prov, name=splited_name[1], version=splited_name[2])

            if not resource.open:
                user_profile = UserProfile.objects.get(user=request.user)
                found = False

                # Check if the user has purchased an offering with the resource 
                # only if the offering is not open
            
                for off in user_profile.offerings_purchased:
                    o = Offering.objects.get(pk=off)

                    for res in o.resources:
                        if str(res) == resource.pk:
                            found = True
                            break

                    if found:
                        break

                if not found:
                    # Check if the user organization has an offering with the resource
                    for off in user_profile.current_organization.offerings_purchased:
                        o = Offering.objects.get(pk=off)

                        for res in o.resources:
                            if str(res) == resource.pk:
                                found = True
                                break

                        if found:
                            break

                    if not found:
                        return build_response(request, 404, 'Not found')

        if dir_path.endswith('bills'):
            if request.user.is_anonymous():
                return build_response(request, 401, 'Unauthorized')

            user_profile = UserProfile.objects.get(user=request.user)
            #purchase = Purchase.objects.get(ref=name[:24])

            #if purchase.organization_owned:
            #    user_org = user_profile.current_organization
            #    if not purchase.owner_organization.name == user_org.name:
            #        return build_response(request, 404, 'Not found')
            #else:
            #    if not purchase.customer == request.user:
            #        return build_response(request, 404, 'Not found')

        local_path = os.path.join(dir_path, name)

        if not os.path.isfile(local_path):
            return build_response(request, 404, 'Not found')

        if not getattr(settings, 'USE_XSENDFILE', False):
            return serve(request, local_path, document_root='/')
        else:
            response = HttpResponse()
            response['X-Sendfile'] = smart_str(local_path)
            return response
