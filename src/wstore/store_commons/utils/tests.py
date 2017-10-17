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

from wstore.store_commons.utils.units import CurrencyCode


class CurrencyCodeUnitsTestCase(TestCase):

    tags = ('units',)

    def setUp(self):
        self.cc_valid = {
            'title': 'Euro',
            'value': 'EUR',
        }
        self.cc_not_valid = {
            'title': 'Canada Dollar',
            'value': 'CAD',
        }

        settings.CURRENCY_CODES = [
            (self.cc_valid['value'], self.cc_valid['title']),
        ]

    def test_should_check_if_given_value_in_lowercase_exists(self):
        value = self.cc_valid['value'].lower()
        self.assertTrue(CurrencyCode.contains(value))

    def test_should_check_if_given_value_in_uppercase_exists(self):
        value = self.cc_valid['value']
        self.assertTrue(CurrencyCode.contains(value))

    def test_should_check_if_given_value_does_not_exist(self):
        value = self.cc_not_valid['value']
        self.assertFalse(CurrencyCode.contains(value))

    def test_should_parse_tuple_to_dict(self):
        dict_expected = [
            self.cc_valid,
        ]
        self.assertEqual(CurrencyCode.to_dict(), dict_expected)
