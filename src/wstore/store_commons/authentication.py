# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2015 CoNWeT Lab., Universidad Politécnica de Madrid

# This file belongs to the business-charging-backend
# of the Business API Ecosystem.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.contrib.auth import logout as django_logout
from django.http import HttpResponseRedirect
from django.conf import settings

from wstore.store_commons.utils.http import build_response
from wstore.store_commons.utils.url import add_slash


class Http403(Exception):
    pass


def logout(request):

    django_logout(request)
    response = None

    if settings.PORTALINSTANCE:
        # Check if the logout request is originated in a different domain
        if 'HTTP_ORIGIN' in request.META:
            origin = request.META['HTTP_ORIGIN']
            origin = add_slash(origin)

            from wstore.views import ACCOUNT_PORTAL_URL, CLOUD_PORTAL_URL, MASHUP_PORTAL_URL, DATA_PORTAL_URL

            allowed_origins = [
                add_slash(ACCOUNT_PORTAL_URL),
                add_slash(CLOUD_PORTAL_URL),
                add_slash(MASHUP_PORTAL_URL),
                add_slash(DATA_PORTAL_URL)
            ]

            if origin in allowed_origins:
                headers = {
                    'Access-Control-Allow-Origin': origin,
                    'Access-Control-Allow-Credentials': 'true'
                }
                response = build_response(request, 200, 'OK', headers=headers)
            else:
                response = build_response(request, 403, 'Forbidden')

        else:
            # If using the FI-LAB authentication and it is not a cross domain
            # request redirect to the FI-LAB main page
            response = build_response(request, 200, 'OK')

    # If not using the FI-LAB authentication redirect to the login page
    url = '/login?next=/'
    response = HttpResponseRedirect(url)

    return response
