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

import json
from mock import MagicMock
from urllib2 import HTTPError
from nose_parameterized import parameterized

from django.test import TestCase
from django.conf import settings

from wstore.admin.users import views
from wstore.store_commons.utils import http
from wstore.store_commons.utils.testing import decorator_mock, build_response_mock,\
    decorator_mock_callable

__test__ = False


class UserEntryTestCase(TestCase):

    tags = ('user-admin',)

    @classmethod
    def setUpClass(cls):
        # Mock class decorators
        http.authentication_required = decorator_mock
        http.supported_request_mime_types = decorator_mock_callable
        reload(views)

        super(UserEntryTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        # Restore mocked decorators
        reload(http)
        reload(views)
        super(UserEntryTestCase, cls).tearDownClass()

    def setUp(self):

        # Create mock request
        user_object = MagicMock()
        user_object.is_staff = False
        user_object.pk = '2222'
        user_object.userprofile.actor_id = 2
        user_object.username = 'test_user'

        self.request = MagicMock()
        self.request.META.get.return_value = 'application/json'
        self.request.user = user_object

        # Mock user
        views.User = MagicMock()
        views.User.objects.get = MagicMock()
        views.User.objects.get.return_value = user_object

        views.Organization = MagicMock()
        self.org = MagicMock()
        self.org.name = 'test_org'
        self.org.managers = []
        views.Organization.objects.get.return_value = self.org

    def _basic_user(self):
        self.request.user.userprofile.complete_name = 'Test user'
        self.request.user.userprofile.current_organization.name = 'test_user'
        self.request.user.userprofile.organizations = [{
            'organization': '11111',
            'roles': ['customer']
        }]
        self.request.user.userprofile.tax_address = {
            'street': 'fakestreet'
        }
        self.request.user.userprofile.get_user_roles.return_value = ['provider']

    def _org_manager_staff(self):
        self._basic_user()
        self.request.user.userprofile.is_user_org.return_value = False
        self.org.managers = ['2222']
        self.request.user.is_staff = True

    def _forbidden(self):
        self.request.user.username = 'invalid'

    @parameterized.expand([
        ('basic', _basic_user, 200, {
            'href': 'http://domain.com/charging/api/userManagement/users/test_user',
            'id': 'test_user',
            'completeName': 'Test user',
            'currentOrganization': 'test_user',
            'organizations': [{
                'name': 'test_org',
                'roles': ['customer']
            }],
            'roles': ['provider'],
            'billingAddress': {
                'street': 'fakestreet'
            }
        }),
        ('org_manager_staff', _org_manager_staff, 200, {
            'href': 'http://domain.com/charging/api/userManagement/users/test_user',
            'id': 'test_user',
            'completeName': 'Test user',
            'currentOrganization': 'test_user',
            'organizations': [{
                'name': 'test_org',
                'roles': ['customer', 'manager']
            }],
            'roles': ['provider', 'admin'],
            'billingAddress': {
                'street': 'fakestreet'
            }
        }),
        ('forbidden', _forbidden, 403, {
            'result': 'error',
            'message': 'You are not authorized to retrieve user info'
        })
    ])
    def test_get_user(self, name, user_filler, status, response):
        # Mock context
        views.Context = MagicMock()
        cntx_instance = MagicMock()
        cntx_instance.site.domain = 'http://domain.com'
        views.Context.objects.all.return_value = [cntx_instance]

        user_filler(self)

        user_entry = views.UserProfileEntry(permitted_methods=('GET', 'PATCH'))

        result = user_entry.read(self.request, 'test_user')

        # Check result
        self.assertEquals(status, result.status_code)
        self.assertEquals(response, json.loads(result.content))

        if status == 200:
            # Check calls
            views.Context.objects.all.assert_called_once_with()
            views.Organization.objects.get.assert_called_once_with(pk='11111')

    def _invalid_data(self):
        self.request.body = 'invalid'

    CORRECT_RES = {
        'result': 'correct',
        'message': 'OK'
    }

    @parameterized.expand([
        ('complete', {
            'billingAddress': {
                'street': 'fakestreet',
                'postal': '12345',
                'city': 'a city',
                'province': 'a province',
                'country': 'a country'
            }
        }, 200, CORRECT_RES),
        ('street', {
            'billingAddress': {
                'street': 'fakestreet'
            }
        }, 200, CORRECT_RES),
        ('postal', {
            'billingAddress': {
                'postal': '12345'
            }
        }, 200, CORRECT_RES),
        ('city', {
            'billingAddress': {
                'city': 'a city',
            }
        }, 200, CORRECT_RES),
        ('province', {
            'billingAddress': {
                'province': 'a province'
            }
        }, 200, CORRECT_RES),
        ('country', {
            'billingAddress': {
                'country': 'a country'
            }
        }, 200, CORRECT_RES),
        ('none', {}, 200, CORRECT_RES),
        ('forbidden', {}, 403, {
            'result': 'error',
            'message': 'You are not authorized to update user info'
        }, _forbidden),
        ('invalid_data', {}, 400, {
            'result': 'error',
            'message': 'Invalid JSON content'
        }, _invalid_data)
    ])
    def test_user_update(self, name, data, status, response, side_effect=None):

        self.request.user.userprofile.tax_address = {}

        # Include data request
        self.request.body = json.dumps(data)

        # Create view class
        user_entry = views.UserProfileEntry(permitted_methods=('GET', 'PATCH'))

        # Create side effect if needed
        if side_effect:
            side_effect(self)

        # Call the view
        result = user_entry.patch(self.request, 'test_user')

        # Check result
        self.assertEquals(status, result.status_code)
        self.assertEquals(response, json.loads(result.content))

        # Check modified profile
        if status == 200 and 'billingAddress' in data:
            self.assertEquals(data['billingAddress'], self.request.user.userprofile.tax_address)
            self.request.user.userprofile.save.assert_called_once_with()
        else:
            # Check that userprofile has not been modified
            self.assertEquals({}, self.request.user.userprofile.tax_address)
            self.assertFalse(self.request.user.userprofile.save.called)