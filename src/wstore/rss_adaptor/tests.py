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


from mock import MagicMock
from nose_parameterized import parameterized

from django.test import TestCase
from django.conf import settings

from wstore.rss_adaptor import rss_adaptor, rss_manager, model_manager


class RSSAdaptorTestCase(TestCase):

    tags = ('rss-adaptor',)

    def setUp(self):
        settings.WSTOREMAIL = 'testmail@mail.com'
        settings.RSS = 'http://testhost.com/rssHost/'
        settings.STORE_NAME = 'wstore'

        rss_adaptor.requests = MagicMock()
        self._response = MagicMock()
        rss_adaptor.requests.post.return_value = self._response

    def test_rss_client(self):
        # Create mocks
        self._response.status_code = 201

        rss_ad = rss_adaptor.RSSAdaptor()

        rss_ad.send_cdr([{
            'provider': 'test_provider',
            'correlation': '2',
            'purchase': '1234567890',
            'offering': 'test_offering',
            'product_class': 'SaaS',
            'description': 'The description',
            'cost_currency': 'EUR',
            'cost_value': '10',
            'tax_value': '0.0',
            'time_stamp': '10-05-13 10:00:00',
            'customer': 'test_customer',
            'event': 'One time'
        }])

        rss_adaptor.requests.post.assert_called_once_with(
            'http://testhost.com/rssHost/rss/cdrs', json=[{
                'cdrSource': 'testmail@mail.com',
                'productClass': 'SaaS',
                'correlationNumber': '2',
                'timestamp': '10-05-13T10:00:00Z',
                'application': 'test_offering',
                'transactionType': 'C',
                'event': 'One time',
                'referenceCode': '1234567890',
                'description': 'The description',
                'chargedAmount': '10',
                'chargedTaxAmount': '0.0',
                'currency': 'EUR',
                'customerId': 'test_customer',
                'appProvider': 'test_provider'
            }],
            headers={
                'content-type': 'application/json',
                'X-Actor-ID': 'wstore',
                'X-Roles': 'provider',
                'X-Email': 'testmail@mail.com'
            })

    def test_rss_remote_error(self):
        # Create Mocks
        self._response.status_code = 500


class ModelManagerTestCase(TestCase):

    tags = ('rs-models', )

    @classmethod
    def setUpClass(cls):
        # Save used libraries
        cls._old_RSS = rss_manager.RSS

        # Create Mocks
        cls.rss_mock = MagicMock()
        cls.opener = MagicMock()
        cls.mock_response = MagicMock()
        cls.opener.open.return_value = cls.mock_response

        rss_manager.RSS = MagicMock()
        rss_manager.RSS.objects.get.return_value = cls.rss_mock
        super(ModelManagerTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        rss_manager.RSS = cls._old_RSS
        reload(rss_manager)
        super(ModelManagerTestCase, cls).tearDownClass()

    def setUp(self):
        self.rss_mock.reset_mock()
        self.rss_mock.host = 'http://testrss.com/'
        self.manager = model_manager.ModelManagerV1(self.rss_mock, 'accesstoken')
        self.manager._make_request = MagicMock()
        TestCase.setUp(self)

    @parameterized.expand([
        ('complete_model', {
            'class': 'app',
            'percentage': 20.0
        }),
        ('complete_provider',  {
            'class': 'app',
            'percentage': 20.0
        }, 'test_user'),
        ('missing_class', {
            'percentage': 20.0
        }, None, ValueError, 'Missing a required field in model info'),
        ('missing_perc', {
            'class': 'app'
        }, None, ValueError, 'Missing a required field in model info'),
        ('inv_data', ('app', 20.0), None, TypeError, 'Invalid type for model info'),
        ('inv_class', {
            'class': 7,
            'percentage': 20.0
        }, None, TypeError, 'Invalid type for class field'),
        ('inv_percentage', {
            'class': 'app',
            'percentage': '20.0'
        }, None, TypeError, 'Invalid type for percentage field'),
        ('bigger_perc', {
            'class': 'app',
            'percentage': 102.0
        }, None, ValueError, 'The percentage must be a number between 0 and 100')
    ])
    def test_create_model(self, name, data, provider=None, err_type=None, err_msg=None):

        error = None
        try:
            self.manager.create_revenue_model(data, provider)
        except Exception as e:
            error = e

        if not err_type:
            self.assertEquals(error, None)
            # Check calls
            if provider:
                exp_prov = provider
            else:
                exp_prov = settings.STORE_NAME.lower() + '-provider'

            exp_data = {
                'appProviderId': exp_prov,
                'productClass': data['class'],
                'percRevenueShare': data['percentage']
            }
            self.manager._make_request.assert_called_with('POST', 'http://testrss.com/fiware-rss/rss/rsModelsMgmt', exp_data)
        else:
            self.assertTrue(isinstance(error, err_type))
            self.assertEquals(unicode(e), err_msg)

    @parameterized.expand([
        ('default_prov',),
        ('provider', 'test_user')
    ])
    def test_get_model(self, name, provider=None):

        mock_models = [{
            'appProviderId': 'wstore',
            'productClass': 'app',
            'percRevenueShare': 20.0
        }]
        self.manager._make_request.return_value = mock_models

        # Call the get method
        error = False
        try:
            models = self.manager.get_revenue_models(provider)
        except:
            error = True

        # Check no error occurs
        self.assertFalse(error)

        # Check calls
        if not provider:
            provider = settings.STORE_NAME.lower() + '-provider'

        from urllib import quote
        self.manager._make_request.assert_called_once_with('GET', 'http://testrss.com/fiware-rss/rss/rsModelsMgmt?appProviderId=' + quote(provider))

        # Check returned value
        self.assertEquals(models, mock_models)
