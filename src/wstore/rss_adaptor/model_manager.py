# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2016 CoNWeT Lab., Universidad Politécnica de Madrid

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

from django.conf import settings

from wstore.rss_adaptor.rss_manager import RSSManager


class ModelManager(RSSManager):

    def create_revenue_model(self, model_info, provider=None):
        """
        Creates a revenue sharing model in the Revenue Sharing and
        Settlement system
        """
        self._manage_rs_model(provider, model_info, 'POST')

    def update_revenue_model(self, model_info, provider=None):
        """
        Updates a revenue sharing model in the Revenue Sharing and
        Settlement system
        """
        self._manage_rs_model(provider, model_info, 'PUT')

    def _check_model_value(self, field, model_info):
        if field not in model_info:
            raise ValueError('Missing a required field in model info: ' + field)

        try:
            float(model_info[field])
        except:
            raise TypeError('Invalid type for ' + field + ' field')

        if model_info['ownerValue'] < 0 or model_info['ownerValue'] > 100:
            raise ValueError(field + ' must be a number between 0 and 100')

    def _manage_rs_model(self, provider, model_info, method):
        if not provider:
            provider = settings.STORE_NAME.lower() + '-provider'

        self._check_model_value('ownerValue', model_info)
        self._check_model_value('aggregatorValue', model_info)

        if 'productClass' not in model_info:
            raise ValueError('Missing a required field in model info: productClass')

        if not isinstance(model_info['productClass'], unicode) and not isinstance(model_info['productClass'], str):
            raise TypeError('Invalid type for productClass field')

        # Validate RS model
        model_info['aggregatorId'] = settings.WSTOREMAIL
        model_info['aggregatorValue'] = unicode(model_info['aggregatorValue'])
        model_info['ownerProviderId'] = provider
        model_info['ownerValue'] = unicode(model_info['ownerValue'])
        model_info['algorithmType'] = 'FIXED_PERCENTAGE'

        if 'stakeholders' not in model_info:
            model_info['stakeholders'] = []

        endpoint = settings.RSS + 'rss/models'

        self._make_request('POST', endpoint, model_info)
