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

from wstore.asset_manager.models import ResourcePlugin, Resource
from wstore.store_commons.utils.url import is_valid_url
from wstore.asset_manager.errors import ProductError
from wstore.models import Context


class ProductValidator():

    def _get_characteristic_value(self, characteristic):
        if len(characteristic['productSpecCharacteristicValue']) > 1:
            raise ProductError('The characteristic ' + characteristic['name'] + ' must not contain multiple values')

        return characteristic['productSpecCharacteristicValue'][0]['value']

    def _parse_characteristics(self, product_spec):
        expected_chars = {
            'asset type': [],
            'media type': [],
            'location': []
        }

        if 'productSpecCharacteristic' not in product_spec:
            raise ProductError('The product specification does not contain the productSpecCharacteristic field')

        # Extract the needed characteristics for processing digital assets
        for char in product_spec['productSpecCharacteristic']:
            if char['name'].lower() in expected_chars:
                expected_chars[char['name'].lower()].append(self._get_characteristic_value(char))

        for char_name in expected_chars:
            # Validate the existance of the characteristic
            if not len(expected_chars[char_name]):
                raise ProductError('The product specification must contain a ' + char_name + ' characteristic')

            # Validate that only a value has been provided
            if len(expected_chars[char_name]) > 1:
                raise ProductError('The product specification must not contain more than one ' + char_name + ' characteristic')

        return expected_chars['asset type'][0], expected_chars['media type'][0], expected_chars['location'][0]

    def validate_creation(self, provider, product_spec):
        # Extract product needed characteristics
        asset_t, media_type, url = self._parse_characteristics(product_spec)

        # Search the asset type
        try:
            asset_type = ResourcePlugin.objects.get(name=asset_t)
        except:
            raise ProductError('The given product specification contains a not supported asset type: ' + asset_t)

        # Validate media type
        if len(asset_type.media_types) and media_type not in asset_type.media_types:
            raise ProductError('The media type characteristic included in the product specification is not valid for the given asset type')

        # Validate location format
        if not is_valid_url(url):
            raise ProductError('The location characteristic included in the product specification is not a valid URL')

        # Check if format is FILE
        is_file = False
        if 'FILE' in asset_type.formats:
            if 'URL' in asset_type.formats:
                site = Context.objects.all()[0].site
                if url.startswith(site.domain):
                    is_file = True
            else:
                is_file = True

        # If the asset is a file it must have been uploaded
        if is_file:
            try:
                asset = Resource.objects.get(download_link=url)
            except:
                raise ProductError('The URL specified in the location characteristic does not point to a valid digital asset')

            if asset.provider != provider:
                raise PermissionDenied('You are not authorized to use the digital asset specified in the location characteristic')

            if asset.content_type != media_type.lower():
                raise ProductError('The specified media type characteristic is different from the one of the provided digital asset')
        else:
            # Create the new asset model
            asset = Resource.objects.create(
                resource_path='',
                download_link=url,
                provider=provider,
                content_type=media_type
            )

        # Complete asset information
        asset.version = product_spec['version']
        asset.resource_type = asset_t
        asset.state = product_spec['lifecycleStatus']
        asset.save()

    def validate_update(self, provider, product_spec):
        pass

    def validate_upgrade(self, provider, product_spec):
        pass

    def validate_deletion(self, provider, product_spec):
        pass

    def validate(self, action, provider, product_spec):
        validators = {
            'create': self.validate_creation,
            'update': self.validate_update,
            'upgrade': self.validate_upgrade,
            'delete': self.validate_deletion
        }

        if action not in validators:
            msg = 'The provided action (' + action
            msg += ') is not valid. Allowed values are create, update, upgrade, and delete'
            raise ValueError(msg)

        validators[action](provider, product_spec)
