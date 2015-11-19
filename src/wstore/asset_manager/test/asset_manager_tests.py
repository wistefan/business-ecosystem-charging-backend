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

from mock import MagicMock
from nose_parameterized import parameterized

from django.test import TestCase

from wstore.asset_manager import asset_manager
from wstore.asset_manager.test.resource_test_data import *


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
