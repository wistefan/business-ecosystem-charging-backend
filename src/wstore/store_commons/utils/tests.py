# -*- coding: utf-8 -*-

# Copyright (c) 2017 CoNWeT Lab., Universidad Politécnica de Madrid

# This file belongs to the business-charging-backend
# of the Business API Ecosystem.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings

from nose_parameterized import parameterized

from wstore.store_commons.utils.units import ChargePeriod, CurrencyCode


@override_settings(
    CHARGE_PERIODS={
        'daily': 1,
    },
    CURRENCY_CODES=[
        ('EUR', 'Euro'),
    ],
)
class UnitsTestCase(TestCase):

    tags = ('units',)

    def setUp(self):
        self.charge_period_valid = {
            'title': 'daily',
            'value': 1,
        }
        self.charge_period_not_valid = {
            'title': 'weekly',
            'value': 7,
        }

        self.currency_code_valid = {
            'title': 'Euro',
            'value': 'EUR',
        }
        self.currency_code_not_valid = {
            'title': 'Canada Dollar',
            'value': 'CAD',
        }

    @parameterized.expand([
        ("charge_period", ChargePeriod, 'title'),
        ("currency_code", CurrencyCode, 'value'),
    ])
    def test_should_check_if_given_value_in_lowercase_exists(self, name, ns, attr):
        self.assertTrue(ns.contains(getattr(self, name + '_valid')[attr].lower()))

    @parameterized.expand([
        ("charge_period", ChargePeriod, 'title'),
        ("currency_code", CurrencyCode, 'value'),
    ])
    def test_should_check_if_given_value_in_uppercase_exists(self, name, ns, attr):
        self.assertTrue(ns.contains(getattr(self, name + '_valid')[attr].upper()))

    @parameterized.expand([
        ("charge_period", ChargePeriod, 'title'),
        ("currency_code", CurrencyCode, 'value'),
    ])
    def test_should_check_if_given_value_does_not_exist(self, name, ns, attr):
        self.assertFalse(ns.contains(getattr(self, name + '_not_valid')[attr].upper()))

    # charge period
    def test_should_get_value_when_given_title_in_lowercase_exists(self):
        title = self.charge_period_valid['title']
        value_expected = self.charge_period_valid['value']
        self.assertEquals(ChargePeriod.get_value(title), value_expected)

    def test_should_get_value_when_given_title_in_uppercase_exists(self):
        title = self.charge_period_valid['title'].upper()
        value_expected = self.charge_period_valid['value']
        self.assertEquals(ChargePeriod.get_value(title), value_expected)

    def test_should_get_none_when_given_title_does_not_exist(self):
        title = self.charge_period_not_valid['title']
        self.assertIsNone(ChargePeriod.get_value(title))

    @parameterized.expand([
        ("charge_period", ChargePeriod),
        ("currency_code", CurrencyCode),
    ])
    def test_should_parse_to_json(self, name, ns):
        dict_expected = [
            getattr(self, name + '_valid'),
        ]
        self.assertEqual(ns.to_json(), dict_expected)
