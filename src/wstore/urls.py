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

from django.conf.urls import patterns, url

from wstore.admin.users import views as user_views
from wstore.asset_manager import views as offering_views
from wstore.asset_manager.resource_plugins import views as plugins_views
from wstore.ordering import views as ordering_views
from wstore.charging_engine import views as charging_views

urlpatterns = patterns('',
    # API
    url(r'^charging/api/userManagement/users/(?P<username>[\w -]+)/?$', user_views.UserProfileEntry(permitted_methods=('GET', 'PATCH'))),
    url(r'^charging/api/assetManagement/assets/?$', offering_views.AssetCollection(permitted_methods=('GET',))),
    url(r'^charging/api/assetManagement/assets/uploadJob/?$', offering_views.UploadCollection(permitted_methods=('POST',))),
    url(r'^charging/api/assetManagement/assets/validateJob/?$', offering_views.ValidateCollection(permitted_methods=('POST',))),
    url(r'^charging/api/assetManagement/assetTypes/?$', plugins_views.PluginCollection(permitted_methods=('GET', ))),
    url(r'^charging/api/assetManagement/assetTypes/(?P<plugin_id>[\w -]+)/?$', plugins_views.PluginEntry(permitted_methods=('GET',))),

    url(r'^charging/api/orderManagement/orders/?$', ordering_views.OrderingCollection(permitted_methods=('POST',))),
    url(r'^charging/api/orderManagement/orders/(?P<reference>[\w]+)/accept/?$', charging_views.PayPalConfirmation(permitted_methods=('GET',))),
    url(r'^charging/api/orderManagement/orders/(?P<reference>[\w]+)/cancel/?$', charging_views.PayPalCancelation(permitted_methods=('GET',)))
)
