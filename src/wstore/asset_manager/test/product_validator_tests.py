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
from django.core.exceptions import PermissionDenied

from mock import MagicMock
from nose_parameterized import parameterized

from django.test.testcases import TestCase

from wstore.asset_manager import product_validator
from wstore.asset_manager.errors import ProductError
from wstore.asset_manager.test.product_validator_test_data import *


class ProductValidatorTestCase(TestCase):

    tags = ('product-validator', )

    def setUp(self):
        self._provider = MagicMock()

        product_validator.ResourcePlugin = MagicMock()
        self._plugin_instance = MagicMock()
        self._plugin_instance.media_types = ['application/x-widget']
        self._plugin_instance.formats = ["FILE"]
        product_validator.ResourcePlugin.objects.get.return_value = self._plugin_instance

        product_validator.Resource = MagicMock()
        self._asset_instance = MagicMock()
        self._asset_instance.content_type = 'application/x-widget'
        self._asset_instance.provider = self._provider
        product_validator.Resource.objects.get.return_value = self._asset_instance
        product_validator.Resource.objects.create.return_value = self._asset_instance

        # Mock Site
        product_validator.Context = MagicMock()
        self._context_inst = MagicMock()
        self._context_inst.site.domain = "http://testlocation.org/"
        product_validator.Context.objects.all.return_value = [self._context_inst]

    def _support_url(self):
        self._plugin_instance.formats = ["FILE", "URL"]

    def _only_url(self):
        self._plugin_instance.formats = ["URL"]

    def _not_supported(self):
        product_validator.ResourcePlugin.objects.get.side_effect = Exception('Not found')

    def _inv_media(self):
        self._plugin_instance.media_types = ['text/plain']

    def _not_asset(self):
        product_validator.Resource.objects.get.side_effect = Exception('Not found')

    def _not_owner(self):
        self._asset_instance.provider = MagicMock()

    def _diff_media(self):
        self._asset_instance.content_type = 'text/plain'

    @parameterized.expand([
        ('basic', BASIC_PRODUCT, ),
        ('file_url_allowed', BASIC_PRODUCT, _support_url),
        ('url_asset', BASIC_PRODUCT, _only_url),
        ('invalid_action', INVALID_ACTION, None, ValueError, 'The provided action (invalid) is not valid. Allowed values are create, update, upgrade, and delete'),
        ('missing_chars', MISSING_CHAR, None, ProductError, 'ProductError: The product specification does not contain the productSpecCharacteristic field'),
        ('missing_media', MISSING_MEDIA, None, ProductError, 'ProductError: The product specification must contain a media type characteristic'),
        ('missing_type', MISSING_TYPE, None, ProductError, 'ProductError: The product specification must contain a asset type characteristic'),
        ('missing_location', MISSING_LOCATION, None, ProductError, 'ProductError: The product specification must contain a location characteristic'),
        ('multiple_char', MULTIPLE_LOCATION, None, ProductError, 'ProductError: The product specification must not contain more than one location characteristic'),
        ('not_supported', BASIC_PRODUCT, _not_supported, ProductError, 'ProductError: The given product specification contains a not supported asset type: Widget'),
        ('inv_media', BASIC_PRODUCT, _inv_media, ProductError, 'ProductError: The media type characteristic included in the product specification is not valid for the given asset type'),
        ('inv_location', INVALID_LOCATION, None, ProductError, 'ProductError: The location characteristic included in the product specification is not a valid URL'),
        ('not_asset', BASIC_PRODUCT, _not_asset, ProductError, 'ProductError: The URL specified in the location characteristic does not point to a valid digital asset'),
        ('unauthorized', BASIC_PRODUCT, _not_owner, PermissionDenied, 'You are not authorized to use the digital asset specified in the location characteristic'),
        ('diff_media', BASIC_PRODUCT, _diff_media, ProductError, 'ProductError: The specified media type characteristic is different from the one of the provided digital asset')
    ])
    def test_validate_creation(self, name, data, side_effect=None, err_type=None, err_msg=None):

        if side_effect is not None:
            side_effect(self)

        error = None
        try:
            validator = product_validator.ProductValidator()
            validator.validate(data['action'], self._provider, data['product'])
        except Exception as e:
            error = e

        if err_type is None:
            self.assertTrue(error is None)
            # Check calls
            product_validator.ResourcePlugin.objects.get.assert_called_once_with(name='Widget')

            if "FILE" in self._plugin_instance.formats:
                product_validator.Resource.objects.get.assert_called_once_with(download_link="http://testlocation.org/media/resources/test_user/widget.wgt")
            else:
                product_validator.Resource.objects.create.assert_called_once_with(
                    content_path='',
                    download_link="http://testlocation.org/media/resources/test_user/widget.wgt",
                    provider=self._provider
                )

            # Check asset values
            self.assertEquals("2.0", self._asset_instance.version)
            self.assertEquals('Widget', self._asset_instance.resource_type)
            self.assertEquals("Active", self._asset_instance.state)
            self._asset_instance.save.assert_called_once_with()
        else:
            self.assertTrue(isinstance(error, err_type))
            self.assertEquals(err_msg, unicode(e))
