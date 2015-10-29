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
from bson import ObjectId

from django.conf import settings
from django.core.exceptions import PermissionDenied

from wstore.models import Resource, Offering
from wstore.asset_manager.models import ResourceVersion
from wstore.store_commons.utils.name import is_valid_file
from wstore.store_commons.utils.url import is_valid_url
from wstore.store_commons.utils.version import Version
from wstore.store_commons.errors import ConflictError
from wstore.asset_manager.offerings_management import delete_offering
from wstore.asset_manager.resource_plugins.decorators import register_resource_events, \
    upgrade_resource_events, update_resource_events, delete_resource_events, \
    register_resource_validation_events, upgrade_resource_validation_events


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


@register_resource_events
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


@register_resource_validation_events
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

    if not file_:
        if 'content' not in data:
            raise ValueError('The digital asset file has not been provided')

        resource_data['content_path'] = _save_resource_file(current_organization.name, data['content'])
        resource_data['link'] = ''

    else:
        resource_data['content_path'] = _save_resource_file(current_organization.name, file_)
        resource_data['link'] = ''

    resource_data['metadata'] = data.get('metadata', {})

    return resource_data, current_organization


def upload_asset(provider, data, file_=None):
    """
    Uploads a new digital asset that will be used to create a product Specification
    :param provider: User uploading the digital asset
    :param data: Information of the asset
    :param file_: Digital asset file, in case it has been provided as multipart/form-data
    :returns The href of the digital asset
    """

    resource_data, current_organization = _load_resource_info(provider, data, file_=file_)

    # Create the resource entry in the database
    resource = _create_resource_model(current_organization, resource_data)
    return resource.get_url()


def _get_decorated_save(action):
    save_decorators = {
        'upgrade': upgrade_resource_events,
        'update': update_resource_events
    }

    decorator = save_decorators[action]

    @decorator
    def save_resource(resource):
        resource.save()

    return save_resource


@upgrade_resource_validation_events
def _validate_upgrade_resource_info(resource, data, file_=None):
    # Validate data
    if'version' not in data:
        raise ValueError('Missing a required field: Version')

    # Create version objects
    version = Version(data['version'])
    old_version = Version(resource.version)

    if old_version >= version:
        raise ValueError('The new version cannot be lower that the current version: ' + data['version'] + ' - ' + resource.version)

    # Check resource state
    if resource.state == 'deleted':
        raise PermissionDenied('Deleted resources cannot be upgraded')

    return data


def upgrade_resource(resource, data, file_=None):
    """
    Upgrades an existing resource to a new version
    """

    data = _validate_upgrade_resource_info(resource, data, file_=None)

    # Save the old version
    resource.old_versions.append(ResourceVersion(
        version=resource.version,
        resource_path=resource.resource_path,
        download_link=resource.download_link,
        resource_usdl=resource.resource_usdl,
        resource_uri=resource.resource_uri
    ))

    # Update new version number
    resource.version = data['version']

    # Update asset_manager
    if file_ or 'content' in data:
        if file_:
            file_content = file_
        else:
            file_content = data['content']

        # Create new file
        resource.resource_path = _save_resource_file(resource.provider.name, resource.name, resource.version, file_content)
        resource.download_link = ''
    elif 'link' in data:
        if not is_valid_url(data['link']):
            raise ValueError('Invalid URL format')

        resource.download_link = data['link']
        resource.resource_path = ''
    else:
        raise ValueError('No resource has been provided')

    # Save the resource
    decorated_save = _get_decorated_save('upgrade')
    decorated_save(resource)


def update_resource(resource, data):

    # Check that the resource can be updated
    if resource.state == 'deleted':
        raise PermissionDenied('Deleted resources cannot be updated')

    # If the resource is included in an offering
    # only the resource fields can be updated
    # (not the resource itself)
    if len(resource.offerings):

        invalid_data = False
        for field in data:
            if field != 'description':
                invalid_data = True
                break

        if invalid_data:
            raise PermissionDenied('The resource is being used, only description can be modified')

    # Check that no contents has been provided
    if 'content' in data or 'link' in data:
        raise ValueError('Resource contents cannot be updated. Please upgrade the resource to provide new contents')

    if 'name' in data:
        raise ValueError('Name field cannot be updated since is used to identify the resource')

    if 'version' in data:
        raise ValueError('Version field cannot be updated since is used to identify the resource')

    # Update fields
    if 'content_type' in data:
        if not isinstance(data['content_type'], unicode) and not isinstance(data['content_type'], str):
            raise TypeError('Invalid type for content_type field')

        resource.content_type = data['content_type']

    if 'open' in data:
        if not isinstance(data['open'], bool):
            raise TypeError('Invalid type for open field')

        resource.open = data['open']

    if 'description' in data:
        if not isinstance(data['description'], unicode) and not isinstance(data['description'], str):
            raise TypeError('Invalid type for description field')

        resource.description = data['description']

    decorated_save = _get_decorated_save('update')
    decorated_save(resource)


def get_resource_info(resource):
    return {
        'product_ref': resource.product_ref,
        'version': resource.version,
        'content_type': resource.content_type,
        'state': resource.state,
        'href': resource.get_url(),
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


def _remove_resource(resource):
    # Delete files if needed
    if resource.resource_path:
        path = os.path.join(settings.BASEDIR, resource.resource_path[1:])
        os.remove(path)

    # Remove the resource
    resource.delete()


@delete_resource_events
def _delete_resource(resource, user):

    if not len(resource.offerings):
        _remove_resource(resource)
    else:
        # If the resource is part of an offering check if all the
        # asset_manager are in uploaded state
        used_offerings = []
        for off in resource.offerings:
            offering = Offering.objects.get(pk=off)

            # Remove resource from uploaded asset_manager
            if offering.state == 'uploaded':
                offering.resources.remove(ObjectId(resource.pk))
                offering.save()
            else:
                used_offerings.append(off)

        # If the resource is not included in any offering delete it
        if not len(used_offerings):
            _remove_resource(resource)
        else:
            resource.offerings = used_offerings
            resource.state = 'deleted'
            resource.save()

            # Remove published asset_manager
            for of in used_offerings:
                offering = Offering.objects.get(pk=of)
                if offering.state == 'published':
                    delete_offering(user, offering)


def delete_resource(resource, user):

    if resource.state == 'deleted':
        raise PermissionDenied('The resource is already deleted')

    _delete_resource(resource, user)
