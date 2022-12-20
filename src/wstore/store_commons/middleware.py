# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2016 CoNWeT Lab., Universidad Politécnica de Madrid

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


from __future__ import unicode_literals

from django.utils.importlib import import_module
from django.utils.functional import SimpleLazyObject
from django.utils.http import http_date, parse_http_date_safe


class URLMiddleware(object):

    _middleware = {}

    def load_middleware(self, group):
        """
        Populate middleware lists from settings.URL_MIDDLEWARE_CLASSES.
        """
        from django.conf import settings
        from django.core import exceptions

        middleware = {
            'process_request': [],
            'process_view': [],
            'process_template_response': [],
            'process_response': [],
            'process_exception': [],
        }
        for middleware_path in settings.URL_MIDDLEWARE_CLASSES[group]:
            try:
                mw_module, mw_classname = middleware_path.rsplit('.', 1)
            except ValueError:
                raise exceptions.ImproperlyConfigured('%s isn\'t a middleware module' % middleware_path)
            try:
                mod = import_module(mw_module)
            except ImportError as e:
                raise exceptions.ImproperlyConfigured('Error importing middleware %s: "%s"' % (mw_module, e))
            try:
                mw_class = getattr(mod, mw_classname)
            except AttributeError:
                raise exceptions.ImproperlyConfigured('Middleware module "%s" does not define a "%s" class' % (mw_module, mw_classname))
            try:
                mw_instance = mw_class()
            except exceptions.MiddlewareNotUsed:
                continue

            if hasattr(mw_instance, 'process_request'):
                middleware['process_request'].append(mw_instance.process_request)
            if hasattr(mw_instance, 'process_view'):
                middleware['process_view'].append(mw_instance.process_view)
            if hasattr(mw_instance, 'process_template_response'):
                middleware['process_template_response'].insert(0, mw_instance.process_template_response)
            if hasattr(mw_instance, 'process_response'):
                middleware['process_response'].insert(0, mw_instance.process_response)
            if hasattr(mw_instance, 'process_exception'):
                middleware['process_exception'].insert(0, mw_instance.process_exception)

        # We only assign to this when initialization is complete as it is used
        # as a flag for initialization being complete.
        self._middleware[group] = middleware

    def get_matched_middleware(self, path, middleware_method):

        if path.startswith('/charging/'):
            group = 'api'
        elif path.startswith('/media/'):
            group = 'media'
        else:
            group = 'default'

        if group not in self._middleware:
            self.load_middleware(group)

        return self._middleware[group][middleware_method]

    def process_request(self, request):
        matched_middleware = self.get_matched_middleware(request.path, 'process_request')
        for middleware in matched_middleware:
            response = middleware(request)
            if response:
                return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        matched_middleware = self.get_matched_middleware(request.path, 'process_view')
        for middleware in matched_middleware:
            response = middleware(request, view_func, view_args, view_kwargs)
            if response:
                return response

    def process_template_response(self, request, response):
        matched_middleware = self.get_matched_middleware(request.path, 'process_template_response')
        for middleware in matched_middleware:
            response = middleware(request, response)
        return response

    def process_response(self, request, response):
        matched_middleware = self.get_matched_middleware(request.path, 'process_response')
        for middleware in matched_middleware:
            response = middleware(request, response)
        return response

    def process_exception(self, request, exception):
        matched_middleware = self.get_matched_middleware(request.path, 'process_exception')
        for middleware in matched_middleware:
            response = middleware(request, exception)
            if response:
                return response


def get_api_user(request):
    from django.contrib.auth.models import AnonymousUser
    from django.conf import settings
    from wstore.models import Organization, User

    # Get User information from the request
    token_info = ['bearer', 'token']
    try:
        if settings.PROPAGATE_TOKEN:
            token_info = request.META['HTTP_AUTHORIZATION'].split(' ')

        nick_name = request.META['HTTP_X_NICK_NAME']
        display_name = request.META['HTTP_X_DISPLAY_NAME']
        email = request.META['HTTP_X_EMAIL']
        roles = request.META['HTTP_X_ROLES'].split(',')
        user_name = request.META['HTTP_X_ACTOR']
        external_username = request.META['HTTP_X_EXT_NAME']
        idp = request.META['HTTP_X_IDP_ID']
        if 'HTTP_X_ISSUER_DID' in request.META:
            issuerDid = request.META['HTTP_X_ISSUER_DID']
        else:
            issuerDid = "none"
    except:
        return AnonymousUser()

    if len(token_info) != 2 and token_info[0].lower() != 'bearer':
        return AnonymousUser()

    # Check if the user already exist
    try:
        user = User.objects.get(username=user_name)
    except:
        user = User.objects.create(username=user_name)

    if nick_name == user_name:
        # Update user info
        user.email = email
        user.userprofile.complete_name = display_name
        user.userprofile.actor_id = external_username
        user.is_staff = settings.ADMIN_ROLE.lower() in roles
        user.save()

    user.userprofile.access_token = token_info[1]
    
    user_roles = []

    if settings.PROVIDER_ROLE in roles:
        user_roles.append('provider')

    if settings.CUSTOMER_ROLE in roles:
        user_roles.append('customer')

    # Get or create current organization
    try:
        org = Organization.objects.get(name=nick_name)
    except:
        org = Organization.objects.create(name=nick_name)

    org.private = nick_name == user_name
    org.idp = idp
    org.issuerDid = issuerDid
    org.save()

    user.userprofile.current_roles = user_roles
    user.userprofile.current_organization = org

    # change user.userprofile.current_organization
    user.userprofile.save()

    return user


class AuthenticationMiddleware(object):

    def process_request(self, request):
        request.user = SimpleLazyObject(lambda: get_api_user(request))


class ConditionalGetMiddleware(object):
    """
    Handles conditional GET operations. If the response has a ETag or
    Last-Modified header, and the request has If-None-Match or
    If-Modified-Since, the response is replaced by an HttpNotModified.

    Also sets the Date and Content-Length response-headers.
    """
    def process_response(self, request, response):
        response['Date'] = http_date()
        if not response.has_header('Content-Length'):
            response['Content-Length'] = str(len(response.content))

        if response.has_header('ETag'):
            if_none_match = request.META.get('HTTP_IF_NONE_MATCH')
            if if_none_match == response['ETag']:
                # Setting the status is enough here. The response handling path
                # automatically removes content for this status code (in
                # http.conditional_content_removal()).
                response.status_code = 304

        if response.has_header('Last-Modified'):
            if_modified_since = request.META.get('HTTP_IF_MODIFIED_SINCE')
            if if_modified_since is not None:
                try:
                    # IE adds a length attribute to the If-Modified-Since header
                    separator = if_modified_since.index(';')
                    if_modified_since = if_modified_since[0:separator]
                except:
                    pass
                if_modified_since = parse_http_date_safe(if_modified_since)
            if if_modified_since is not None:
                last_modified = parse_http_date_safe(response['Last-Modified'])
                if last_modified is not None and last_modified <= if_modified_since:
                    # Setting the status code is enough here (same reasons as
                    # above).
                    response.status_code = 304

        return response
