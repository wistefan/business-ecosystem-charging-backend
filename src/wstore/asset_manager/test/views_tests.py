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
from StringIO import StringIO
from nose_parameterized import parameterized

from django.test import TestCase
from django.test.client import RequestFactory, MULTIPART_CONTENT
from django.contrib.auth.models import User

from wstore.asset_manager import views
from wstore.store_commons.errors import ConflictError

RESOURCE_DATA = {
    'content': {
        'name': 'testfile.zip',
        'content': 'content'
    }
}


class AssetCollectionTestCase(TestCase):

    tags = ('asset-api',)

    def setUp(self):
        # Create request factory
        self.factory = RequestFactory()
        # Create testing user
        self.user = User.objects.create_user(username='test_user', email='', password='passwd')
        self.user.userprofile.get_current_roles = MagicMock(name='get_current_roles')
        self.user.userprofile.get_current_roles.return_value = ['provider', 'customer']
        self.user.userprofile.save()
        views.AssetManager = MagicMock()
        self.am_instance = MagicMock()
        views.AssetManager.return_value = self.am_instance

    @classmethod
    def tearDownClass(cls):
        reload(views)
        super(AssetCollectionTestCase, cls).tearDownClass()

    def _no_provider(self):
        self.user.userprofile.get_current_roles = MagicMock(name='get_current_roles')
        self.user.userprofile.get_current_roles.return_value = ['customer']
        self.user.userprofile.save()

    def _call_exception(self):
        self.am_instance.get_provider_assets_info.side_effect = Exception('Getting resources error')

    @parameterized.expand([
        ([{
            'name': 'test_resource',
            'provider': 'test_user',
            'version': '1.0'
        }],),
        ([{
            'name': 'test_resource',
            'provider': 'test_user',
            'version': '1.0'
        }], None, 200, None, {
            'start': '1',
            'limit': '1'
        }),
        ([], _no_provider, 403, 'Forbidden'),
        ([], _call_exception, 400, 'Getting resources error')
    ])
    def test_get_assets(self, return_value, side_effect=None, code=200, error_msg=None, pagination=None):

        # Mock get asset_manager method
        resource_collection = views.AssetCollection(permitted_methods=('GET',))

        self.am_instance.get_provider_assets_info.return_value = return_value

        path = '/api/offering/resources'

        if pagination is not None:
            path += '?start=' + pagination['start'] + '&limit=' + pagination['limit']

        request = self.factory.get(path, HTTP_ACCEPT='application/json')

        request.user = self.user

        # Create the side effect if needed
        if side_effect:
            side_effect(self)

        # Call the view
        response = resource_collection.read(request)

        self.assertEquals(response.status_code, code)
        self.assertEqual(response.get('Content-type'), 'application/json; charset=utf-8')
        body_response = json.loads(response.content)

        if not error_msg:
            views.AssetManager.assert_called_once_with()
            self.am_instance.get_provider_assets_info.assert_called_once_with(self.user, pagination=pagination)
            self.assertEquals(type(body_response), list)
            self.assertEquals(body_response, return_value)
        else:
            self.assertEqual(type(body_response), dict)
            self.assertEqual(body_response['message'], error_msg)
            self.assertEqual(body_response['result'], 'error')

    def _creation_exception(self):
        self.am_instance.upload_asset.side_effect = Exception('Resource creation exception')

    def _existing(self):
        self.am_instance.upload_asset.side_effect = ConflictError('Resource exists')

    @parameterized.expand([
        (RESOURCE_DATA,),
        (RESOURCE_DATA, True),
        (RESOURCE_DATA, False, _no_provider, True, 403, "You don't have the seller role"),
        (RESOURCE_DATA, False, _creation_exception, True, 400, 'Resource creation exception'),
        (RESOURCE_DATA, True, _creation_exception, True, 400, 'Resource creation exception'),
        (RESOURCE_DATA, True, _creation_exception, True, 400, 'Resource creation exception'),
        (RESOURCE_DATA, True, _existing, True, 409, 'Resource exists')
    ])
    def test_create_resource(self, data, file_=False, side_effect=None, error=False, code=201, msg='Created'):

        # Mock get asset_manager method
        resource_collection = views.UploadCollection(permitted_methods=('POST', ))

        content = json.dumps(data)
        content_type = 'application/json'

        if file_:
            f = StringIO()
            f.name = 'test_file.txt'
            f.write('test file')
            content = {
                'json': json.dumps(data),
                'file': f
            }
            content_type = MULTIPART_CONTENT

        # Build the request
        request = self.factory.post(
            '/api/offering/resources',
            content,
            content_type=content_type,
            HTTP_ACCEPT='application/json'
        )

        request.user = self.user

        # Create the side effect if needed
        if side_effect:
            side_effect(self)

        # Call the view
        response = resource_collection.create(request)

        self.assertEqual(response.status_code, code)
        self.assertEqual(response.get('Content-type'), 'application/json; charset=utf-8')
        body_response = json.loads(response.content)

        self.assertEqual(type(body_response), dict)
        self.assertEqual(body_response['message'], msg)

        if not error:
            # Check correct call
            if not file_:
                self.am_instance.upload_asset.assert_called_once_with(self.user, data)
            else:
                expected_file = request.FILES['file']  # The type change when loaded
                self.am_instance.upload_asset.assert_called_once_with(self.user, data, file_=expected_file)

            self.assertEqual(body_response['result'], 'correct')
        else:
            self.assertEqual(body_response['result'], 'error')
