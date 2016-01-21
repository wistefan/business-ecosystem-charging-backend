# -*- coding: utf-8 -*-

# Copyright (c) 2016 CoNWeT Lab., Universidad Politécnica de Madrid

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

import json

from mock import MagicMock, call
from nose_parameterized import parameterized

from django.test import TestCase

from wstore.admin import views


class UnitTestCase(TestCase):

    tags = ('units', )

    def setUp(self):
        views.Unit = MagicMock()
        self.unit_inst = MagicMock()
        views.Unit.return_value = self.unit_inst
        views.Unit.objects.filter.return_value = []

        self.request = MagicMock()
        self.request.user.is_staff = True
        self.request.user.is_anonymous.return_value = False
        self.request.META.get.return_value = 'application/json'

    def _call_read_units(self):
        unit_collection = views.UnitCollection(permitted_methods=('GET', 'POST'))

        response = unit_collection.read(self.request)
        self.assertEquals(200, response.status_code)

        return json.loads(response.content)

    def test_unit_retrieving(self,):
        unit1 = MagicMock()
        unit1.name = 'monthly'
        unit1.defined_model = 'recurring'
        unit1.renovation_period = 30

        unit2 = MagicMock()
        unit2.name = 'calls'
        unit2.defined_model = 'usage'

        views.Unit.objects.all.return_value = [unit1, unit2]
        body = self._call_read_units()

        self.assertEquals([{
            'name': 'monthly',
            'priceType': 'recurring',
            'recurringChargePeriod': 30
        }, {
            'name': 'calls',
            'priceType': 'usage',
        }], body)

    def test_unit_retrieving_empty(self):
        views.Unit.objects.all.return_value = []
        body = self._call_read_units()

        self.assertEquals([], body)

    def _call_create_unit(self, data):
        if isinstance(data, dict):
            data = json.dumps(data)

        self.request.body = data

        unit_collection = views.UnitCollection(permitted_methods=('GET', 'POST'))
        return unit_collection.create(self.request)

    @parameterized.expand([
        ('basic', {
            'name': 'calls',
            'priceType': 'usage'
        }, call(name='calls', defined_model='usage')),
        ('recurring', {
            'name': 'monthly',
            'priceType': 'recurring',
            'recurringChargePeriod': 30
        }, call(name='monthly', defined_model='recurring'))
    ])
    def test_unit_creation(self, name, data, call_):

        response = self._call_create_unit(data)

        self.assertEquals(201, response.status_code)
        body = json.loads(response.content)

        self.assertEquals({
            'result': 'correct',
            'message': 'Created'
        }, body)
        self.assertEquals([call_], views.Unit.call_args_list)
        self.unit_inst.save.assert_called_once_with()

    def _unauthorized(self):
        self.request.user.is_staff = False

    def _existing(self):
        views.Unit.objects.filter.return_value = [{}]

    @parameterized.expand([

        ('unauthorized', {}, 403, 'You are not authorized to register pricing units', _unauthorized),
        ('invalid_json', 'invalid', 400, 'Invalid JSON content'),
        ('missing_name', {
            'priceType': 'recurring'
        }, 400, 'Missing a required field, it must contain name and priceType'),
        ('missing_type', {
            'name': 'monthly'
        }, 400, 'Missing a required field, it must contain name and priceType'),
        ('existing', {
            'name': 'calls',
            'priceType': 'usage'
        }, 409, 'The unit already exists', _existing),
        ('invalid_type', {
            'name': 'calls',
            'priceType': 'invalid'
        }, 400, 'The specified priceType is not valid, must be recurring or usage'),
        ('missing_period', {
            'name': 'monthly',
            'priceType': 'recurring'
        }, 400, 'Recurring price types must contain a recurringChargePeriod')
    ])
    def test_unit_creation_error(self, name, data, exp_code, exp_msg, side_effect=None):

        if side_effect is not None:
            side_effect(self)

        response = self._call_create_unit(data)

        self.assertEquals(exp_code, response.status_code)
        body = json.loads(response.content)

        self.assertEquals({
            'result': 'error',
            'message': exp_msg
        }, body)
        self.assertEquals(0, views.Unit.call_count)
        self.assertEquals(0, self.unit_inst.call_count)
