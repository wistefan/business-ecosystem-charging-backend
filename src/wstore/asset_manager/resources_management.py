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

import base64
import os
from urlparse import urljoin

from django.conf import settings
from django.core.exceptions import PermissionDenied

from wstore.models import Resource, Context
from wstore.asset_manager.models import ResourcePlugin
from wstore.store_commons.utils.name import is_valid_file
from wstore.store_commons.utils.url import is_valid_url
from wstore.store_commons.errors import ConflictError
from wstore.asset_manager.errors import ProductError


def _save_resource_file(provider, file_):
    # Load file contents
    if isinstance(file_, dict):
        file_name = file_['name']
        content = base64.b64decode(file_['data'])
    else:
        file_name = file_.name
        file_.seek(0)
        content = file_.read()

    # Check file name
    if not is_valid_file(file_name):
        raise ValueError('Invalid file name format: Unsupported character')

    # Create provider dir for assets if it does not exists
    provider_dir = os.path.join(settings.MEDIA_ROOT, 'resources')
    provider_dir = os.path.join(provider_dir, provider)

    if not os.path.isdir(provider_dir):
        os.mkdir(provider_dir)

    file_path = os.path.join(provider_dir, file_name)

    # Check if the file already exists
    if os.path.exists(file_path):
        raise ConflictError('The provided digital asset (' + file_name + ') already exists')

    # Create file
    f = open(file_path, "wb")
    f.write(content)
    f.close()

    return settings.MEDIA_URL + 'resources/' + file_name


def _create_resource_model(provider, resource_data):
    # Create the resource
    return Resource.objects.create(
        product_ref=resource_data['product_ref'],
        provider=provider,
        version=resource_data['version'],
        download_link=resource_data['link'],
        resource_path=resource_data['content_path'],
        content_type=resource_data['content_type'],
        resource_type=resource_data['resource_type'],
        state=resource_data['state'],
        meta_info=resource_data['metadata']
    )


def _load_resource_info(provider, data, file_=None):

    # This information will be extracted from the product specification
    resource_data = {
        'product_ref': '',
        'version': '',
        'content_type': '',
        'resource_type': '',
        'state': ''
    }

    current_organization = provider.userprofile.current_organization

    site = Context.objects.all()[0].domain
    if not file_:
        if 'content' not in data:
            raise ValueError('The digital asset file has not been provided')

        resource_data['content_path'] = _save_resource_file(current_organization.name, data['content'])
    else:
        resource_data['content_path'] = _save_resource_file(current_organization.name, file_)

    resource_data['link'] = urljoin(site, resource_data['content_path'])
    resource_data['metadata'] = data.get('metadata', {})

    return resource_data, current_organization


def upload_asset(provider, data, file_=None):
    """
    Uploads a new digital asset that will be used to create a product Specification
    :param provider: User uploading the digital asset
    :param data: Information of the asset
    :param file_: Digital asset file, in case it has been provided as multipart/form-data
    :return: The href of the digital asset
    """

    resource_data, current_organization = _load_resource_info(provider, data, file_=file_)
    resource = _create_resource_model(current_organization, resource_data)

    return resource.get_url()


def get_resource_info(resource):
    return {
        'product_ref': resource.product_ref,
        'version': resource.version,
        'content_type': resource.content_type,
        'state': resource.state,
        'href': resource.download_link,
        'resource_type': resource.resource_type,
        'metadata': resource.meta_info
    }


def get_provider_resources(provider, pagination=None):

    if pagination and ('start' not in pagination or 'limit' not in pagination):
        raise ValueError('Missing required parameter in pagination')

    if pagination and (not int(pagination['start']) > 0 or not int(pagination['limit']) > 0):
        raise ValueError('Invalid pagination limits')

    response = []

    resources = Resource.objects.filter(provider=provider.userprofile.current_organization)

    if pagination:
        x = int(pagination['start']) - 1
        y = x + int(pagination['limit'])

        resources = resources[x:y]

    for res in resources:
        response.append(get_resource_info(res))

    return response


def _get_characteristic_value(characteristic):
    if len(characteristic['productSpecCharacteristicValue']) > 1:
        raise ProductError('The characteristic ' + characteristic['name'] + ' must not contain multiple values')

    return characteristic['productSpecCharacteristicValue'][0]['value']


def _parse_characteristics(product_spec):
    expected_chars = {
        'asset type': [],
        'content type': [],
        'location': []
    }

    if 'productSpecCharacteristic' not in product_spec:
        raise ProductError('The product specification does not contain the productSpecCharacteristic field')

    # Extract the needed characteristics for processing digital assets
    for char in product_spec['productSpecCharacteristic']:
        if char['name'].lower() in expected_chars:
            expected_chars[char['name'].lower()].append(_get_characteristic_value(char))

    for char_name in expected_chars:
        # Validate the existance of the characteristic
        if not len(expected_chars[char_name]):
            raise ProductError('The product specification must contain a ' + char_name + ' characteristic')

        # Validate that only a value has been provided
        if len(expected_chars[char_name]) > 1:
            raise ProductError('The product specification must not contain more than one ' + char_name + ' characteristic')

    return expected_chars


def validate_creation(provider, product_spec):
    # Extract product needed characteristics
    values = _parse_characteristics(product_spec)

    # Search the asset type
    try:
        asset_type = ResourcePlugin.objects.get(name=values['asset type'][0])
    except:
        raise ProductError('The given product specification contains a not supported asset type: ' + values['asset type'][0])

    # Validate media type
    if len(asset_type.media_types) and values['content type'] not in asset_type.media_types:
        raise ProductError('The media type characteristic included in the product specification is not valid for the given asset type')

    # Validate location format
    url = values['location'][0]
    if not is_valid_url(url):
        raise ProductError('The location characteristic included in the product specification is not a valid URL')

    # Check if format is FILE
    is_file = False
    if 'FILE' in asset_type.formats:
        if 'URL' in asset_type.formats:
            site = Context.objects.all()[0]
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
    else:
        # Create the new asset model
        asset = Resource.objects.create(
            content_path='',
            download_link=url,
            provider=provider
        )

    # Complete asset information
    asset.product_ref = product_spec['href']
    asset.version = product_spec['version']
    asset.content_type = values['content type'][0]
    asset.resource_type = values['asset type'][0]
    asset.state = product_spec['lifecycleStatus']
    asset.save()


def validate_update(provider, product_spec):
    pass


def validate_upgrade(provider, product_spec):
    pass


def validate_deletion(provider, product_spec):
    pass
