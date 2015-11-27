# -*- coding: utf-8 -*-

# Copyright (c) 2013-2015 CoNWeT Lab., Universidad Politécnica de Madrid

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
from django.test.utils import override_settings

from mock import MagicMock, mock_open
from nose_parameterized import parameterized

from django.test import TestCase

from wstore.asset_manager import asset_manager
from wstore.asset_manager.test.resource_test_data import *
from wstore.store_commons.errors import ConflictError
from wstore.store_commons.utils.testing import decorator_mock

__test__ = False


class ResourceRetrievingTestCase(TestCase):

    tags = ('asset-manager', )

    def setUp(self):
        # Mock resource model
        resource1 = MagicMock()
        resource1.product_ref = 'http://tmforum.com/catalog/resource1'
        resource1.version = '1.0'
        resource1.content_type = 'text/plain'
        resource1.state = 'Active'
        resource1.download_link = 'http://localhost/media/resources/resource1'
        resource1.resource_type = 'API'
        resource1.meta_info = {}

        resource2 = MagicMock()
        resource2.product_ref = 'http://tmforum.com/catalog/resource2'
        resource2.version = '2.0'
        resource2.content_type = 'text/plain'
        resource2.state = 'Active'
        resource2.open = False
        resource2.download_link = 'http://localhost/media/resources/resource2'
        resource2.resource_type = 'API'
        resource2.meta_info = {}

        resource3 = MagicMock()
        resource3.product_ref = 'http://tmforum.com/catalog/resource3'
        resource3.version = '2.0'
        resource3.content_type = 'text/plain'
        resource3.state = 'Active'
        resource3.open = True
        resource3.download_link = 'http://localhost/media/resources/resource3'
        resource3.resource_type = 'API'
        resource3.meta_info = {}

        resource4 = MagicMock()
        resource4.product_ref = 'http://tmforum.com/catalog/resource4'
        resource4.version = '1.0'
        resource4.content_type = 'text/plain'
        resource4.state = 'Active'
        resource4.open = True
        resource4.download_link = 'http://localhost/media/resources/resource4'
        resource4.resource_type = 'API'
        resource4.meta_info = {}

        asset_manager.Resource = MagicMock()

        asset_manager.Resource.objects.filter.return_value = [
            resource1,
            resource2,
            resource3,
            resource4
        ]

        self.user = MagicMock()
        self.org = MagicMock()
        self.user.userprofile.current_organization = self.org

    @classmethod
    def tearDownClass(cls):
        # Restore resource model
        reload(asset_manager)
        super(ResourceRetrievingTestCase, cls).tearDownClass()

    @parameterized.expand([
        ([RESOURCE_DATA1, RESOURCE_DATA2, RESOURCE_DATA3, RESOURCE_DATA4],),
        ([RESOURCE_DATA1], {"start": 1, "limit": 1}),
        ([RESOURCE_DATA2, RESOURCE_DATA3], {"start": 2, "limit": 2}),
        ([], {"start": 6}, ValueError, "Missing required parameter in pagination"),
        ([], {"limit": 8}, ValueError, "Missing required parameter in pagination"),
        ([], {"start": 0, "limit": 8}, ValueError, "Invalid pagination limits"),
        ([], {"start": 2, "limit": 0}, ValueError, "Invalid pagination limits"),
        ([], {"start": 6, "limit": -1}, ValueError, "Invalid pagination limits"),
        ([], {"start": -6, "limit": 2}, ValueError, "Invalid pagination limits"),
        ([], {"start": 0, "limit": 0}, ValueError, "Invalid pagination limits")
    ])
    def test_resource_retrieving(self, expected_result, pagination=None, err_type=None, err_msg=None):

        # Call the method
        error = None
        try:
            am = asset_manager.AssetManager()
            result = am.get_provider_assets_info(self.user, pagination)
        except Exception as e:
            error = e

        if not err_type:
            # Assert that no error occurs
            self.assertEquals(error, None)
            # Check result
            self.assertEquals(result, expected_result)
        else:
            self.assertTrue(isinstance(error, err_type))
            self.assertEquals(unicode(e), err_msg)



class UploadAssetTestCase(TestCase):

    tags = ('asset-manager', )
    _file = None

    def setUp(self):
        import wstore.store_commons.rollback
        wstore.store_commons.rollback.rollback = decorator_mock

        self._user = MagicMock()
        self._user.userprofile.current_organization.name = 'test_user'

        asset_manager.Context = MagicMock()
        self._context_mock = MagicMock()
        self._context_mock.site.domain = 'http://testdomain.com/'
        asset_manager.Context.objects.all.return_value = [self._context_mock]

        asset_manager.Resource = MagicMock()
        self.res_mock = MagicMock()
        self.res_mock.get_url.return_value = "http://locationurl.com/"
        asset_manager.Resource.objects.create.return_value = self.res_mock

        asset_manager.os.path.isdir = MagicMock()
        asset_manager.os.path.exists = MagicMock()
        asset_manager.os.path.exists.return_value = False

        self.open_mock = mock_open()
        self._old_open = asset_manager.__builtins__['open']
        asset_manager.__builtins__['open'] = self.open_mock

    def tearDown(self):
        import wstore.store_commons.rollback
        reload(wstore.store_commons.rollback)

        self._file = None
        asset_manager.__builtins__['open'] = self._old_open
        reload(asset_manager)

    def _use_file(self):
        # Mock file
        self._file = MagicMock(name="example.wgt")
        self._file.name = "example.wgt"
        self._file.read.return_value = "Test data content"
        asset_manager.os.path.isdir.return_value = False
        asset_manager.os.mkdir = MagicMock()

    def _file_conflict(self):
        asset_manager.os.path.exists.return_value = True

    @parameterized.expand([
        ('basic', UPLOAD_CONTENT),
        ('file', {'contentType': 'application/x-widget'}, _use_file),
        ('inv_file_name', MISSING_TYPE, None, ValueError, 'Missing required field: contentType'),
        ('inv_file_name', UPLOAD_INV_FILENAME, None, ValueError, 'Invalid file name format: Unsupported character'),
        ('existing', UPLOAD_CONTENT, _file_conflict, ConflictError, 'The provided digital asset (example.wgt) already exists'),
        ('not_provided', {'contentType': 'application/x-widget'}, None, ValueError, 'The digital asset file has not been provided')
    ])
    @override_settings(MEDIA_ROOT='/home/test/media')
    def test_upload_asset(self, name, data, side_effect=None, err_type=None, err_msg=None):

        if side_effect is not None:
            side_effect(self)

        am = asset_manager.AssetManager()
        am.rollback_logger = {
            'files': [],
            'models': []
        }

        error = None
        try:
            location = am.upload_asset(self._user, data, file_=self._file)
        except Exception as e:
            error = e

        if err_type is None:
            # Check not error
            self.assertTrue(error is None)

            # Check calls
            self.assertEquals("http://locationurl.com/", location)
            asset_manager.os.path.isdir.assert_called_once_with("/home/test/media/resources/test_user")
            asset_manager.os.path.exists.assert_called_once_with("/home/test/media/resources/test_user/example.wgt")
            self.open_mock.assert_called_once_with("/home/test/media/resources/test_user/example.wgt", "wb")
            self.open_mock().write.assert_called_once_with("Test data content")

            # Check rollback logger
            self.assertEquals({
                'files': ["/home/test/media/resources/test_user/example.wgt"],
                'models': [self.res_mock]
            }, am.rollback_logger)

            # Check file calls
            if self._file is not None:
                self._file.seek.assert_called_once_with(0)
                asset_manager.os.mkdir.assert_called_once_with("/home/test/media/resources/test_user")

            # Check resource creation
            asset_manager.Resource.objects.create.assert_called_once_with(
                product_ref='',
                provider=self._user.userprofile.current_organization,
                version='',
                download_link='http://testdomain.com/media/resources/test_user/example.wgt',
                resource_path='/media/resources/test_user/example.wgt',
                content_type='application/x-widget',
                resource_type='',
                state='',
                meta_info={}
            )
        else:
            self.assertTrue(isinstance(error, err_type))
            self.assertEquals(err_msg, unicode(error))