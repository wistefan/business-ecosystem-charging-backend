# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2016 CoNWeT Lab., Universidad Politécnica de Madrid

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

from copy import deepcopy
from datetime import datetime
from mock import MagicMock
from nose_parameterized import parameterized

from django.test import TestCase
from django.core.exceptions import PermissionDenied

from wstore.charging_engine.accounting import sdr_manager


BASIC_SDR = {
    'orderId': '1',
    'productId': '2',
    'customer': 'test_user',
    'correlationNumber': '1',
    'timestamp': '2015-10-20 17:31:57.838',
    'recordType': 'event',
    'value': '10',
    'unit': 'invocation'
}


class SDRManagerTestCase(TestCase):

    tags = ('sdr',)

    def setUp(self):
        sdr_manager.Organization = MagicMock()
        org = MagicMock()
        org.pk = '1111'
        sdr_manager.Organization.objects.filter.return_value = [org]

        # Create Order mock
        self._order = MagicMock()
        self._order.owner_organization = org

        self._contract = MagicMock()
        self._contract.pricing_model = {
            'pay_per_use': [{
                'unit': 'invocation'
            }]
        }
        self._contract.pending_sdrs = []
        self._contract.applied_sdrs = []

        self._user = MagicMock()
        self._user.userprofile.organizations = [{
            'organization': '1111'
        }]

    def _side_create_applied(self):
        sdr = deepcopy(BASIC_SDR)
        sdr['timestamp'] = datetime.strptime(sdr['timestamp'], '%Y-%m-%d %H:%M:%S.%f')
        self._contract.applied_sdrs = [sdr]

    def _side_create_pending(self):
        sdr = deepcopy(BASIC_SDR)
        sdr['timestamp'] = datetime.strptime(sdr['timestamp'], '%Y-%m-%d %H:%M:%S.%f')
        self._contract.pending_sdrs = [sdr]

    def _side_cust_not_exists(self):
        sdr_manager.Organization.objects.filter.return_value = []

    def _side_user_not_auth(self):
        self._user.userprofile.organizations = [{
            'organization': '2222'
        }]

    def _side_inv_purchase(self):
        self._contract.pricing_model = {
            'global_currency': 'EUR',
            'single_payment': [{
                'value': 10
            }]
        }

    def _side_inv_label(self):
        self._contract.pricing_model = {
            'global_currency': 'EUR',
            'pay_per_use': [{
                'value': 10,
                'unit': 'call'
            }]
        }

    def _mod_inc_corr(self, sdr):
        sdr['correlationNumber'] = 2
        sdr['timestamp'] = '2015-10-20T17:31:57.838123'

    def _mod_inv_time(self, sdr):
        self._mod_inc_corr(sdr)
        sdr['timestamp'] = '1980-05-01 11:10:01.234'

    def _mod_inv_value(self, sdr):
        sdr['value'] = 'a'

    @parameterized.expand([
        ('basic', ),
        ('applied',  0, 1, _mod_inc_corr, _side_create_applied),
        ('pending',  1, 2, _mod_inc_corr, _side_create_pending),
        ('inv_value', 0, 1, _mod_inv_value, None, ValueError, 'The provided value is not a valid number'),
        ('customer_not_existing', 0, 1, None, _side_cust_not_exists, ValueError, 'The specified customer test_user does not exist'),
        ('user_not_auth', 0, 1, None, _side_user_not_auth, PermissionDenied, "You don't belong to the customer organization"),
        ('inv_corr', 0, 1, _mod_inc_corr, None, ValueError, 'Invalid correlation number, expected: 1'),
        ('inv_time', 0, 1, _mod_inv_time, _side_create_applied, ValueError, 'The provided timestamp specifies a lower timing than the last SDR received'),
        ('inv_purch', 0, 1, None, _side_inv_purchase, ValueError, 'The pricing model of the offering does not define pay-per-use components'),
        ('inv_label', 0, 1, None, _side_inv_label, ValueError, 'The specified unit is not included in the pricing model')
    ])
    def test_sdr_feeding(self, name, pos=0, pending=1, mod=None, side_effect=None, err_type=None, err_msg=None):

        sdr = deepcopy(BASIC_SDR)

        if mod is not None:
            mod(self, sdr)

        if side_effect is not None:
            side_effect(self)

        sdr_mng = sdr_manager.SDRManager(self._user, self._order, self._contract)

        error = None
        try:
            sdr_mng.include_sdr(sdr)
        except Exception as e:
            error = e

        if err_type is None:
            self.assertTrue(error is None)
            sdr_manager.Organization.objects.filter.assert_called_once_with(name='test_user')

            self.assertEqual(len(self._contract.pending_sdrs), pending)

            loaded_sdr = self._contract.pending_sdrs[pos]
            self.assertEquals(loaded_sdr, sdr)

            self._order.save.assert_called_once_with()
        else:
            self.assertTrue(isinstance(error, err_type))
            self.assertEquals(unicode(e), err_msg)
