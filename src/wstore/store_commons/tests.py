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
from django.contrib.auth.models import AnonymousUser
from django.test.utils import override_settings

from mock import MagicMock
from nose_parameterized import parameterized

from django.test import TestCase

from wstore.store_commons import middleware, rollback

__test__ = False


@override_settings(ADMIN_ROLE='provider', PROVIDER_ROLE='seller', CUSTOMER_ROLE='customer')
class AuthenticationMiddlewareTestCase(TestCase):

    tags = ('middleware', )

    def setUp(self):
        self.request = MagicMock()
        self.request.META = {
            'HTTP_X_NICK_NAME': 'test-user',
            'HTTP_X_DISPLAY_NAME': 'Test user'
        }

        self._user_model = MagicMock()
        self._user_inst = MagicMock()
        self._user_inst.username = 'test-user'
        self._user_model.objects.get.return_value = self._user_inst
        self._user_model.objects.create.return_value = self._user_inst

        import wstore.models
        wstore.models.User = self._user_model

        self._org_model = MagicMock()
        self._org_instance = MagicMock()
        self._org_instance.pk = 'org'
        self._org_model.objects.get.return_value = self._org_instance

        wstore.models.Organization = self._org_model

    def tearDown(self):
        import wstore.models
        reload(wstore.models)

    def _new_user(self):
        self._user_model.objects.get.side_effect = Exception('Not found')

    def _missing_header(self):
        self.request.META = {}

    @parameterized.expand([
        ('basic', 'provider,seller,', True, ['provider']),
        ('customer', 'customer', False, ['customer']),
        ('new_user', 'seller', False, ['provider'], _new_user),
        ('empty', '', False, []),
        ('missing_header', '', False, [], _missing_header, False, True)
    ])
    def test_get_api_user(self, name, roles, staff, expected_roles, side_effect=None, created=False, anonymous=False):

        self.request.META['HTTP_X_ROLES'] = roles

        if side_effect is not None:
            side_effect(self)

        user = middleware.get_api_user(self.request)

        if not anonymous:
            self.assertEquals(self._user_inst, user)

            # Check user info
            if not created:
                self._user_model.objects.get.assert_called_once_with(username='test-user')
            else:
                self._user_model.objects.create.assert_called_once_with(username='test-user')

            self.assertEquals(self._user_inst.is_staff, staff)

            self._org_model.objects.get.assert_called_once_with(name='test-user')
            self.assertEquals([{'organization': 'org', 'roles': expected_roles}], self._user_inst.userprofile.organizations)

            self.assertEquals('Test user', self._user_inst.userprofile.complete_name)
            self.assertEquals('test-user', self._user_inst.userprofile.actor_id)

            self._user_inst.userprofile.save.assert_called_once_with()
            self._user_inst.save.assert_called_once_with()

        else:
            self.assertEquals(AnonymousUser(), user)


class RollbackTestCase(TestCase):

    tags = ('rollback', )

    def test_rollback_correct(self):
        called_method = MagicMock()
        called_method.return_value = 'Returned'

        wrapper = rollback.rollback(called_method)

        ref = MagicMock()

        value = wrapper(ref, 'value')

        called_method.assert_called_once_with(ref, 'value')
        self.assertEquals('Returned', value)
        self.assertEquals({
            'files': [],
            'models': []
        }, ref.rollback_logger)

    def test_rollback_exception(self):
        model = MagicMock()

        rollback.os = MagicMock()

        def called_method(ref):
            ref.rollback_logger['files'].append('/home/test/testfile.pdf')
            ref.rollback_logger['models'].append(model)
            raise ValueError('Value error')

        wrapper = rollback.rollback(called_method)
        error = False
        try:
            wrapper(MagicMock())
        except ValueError as e:
            error = True
            self.assertEquals('Value error', unicode(e))

        self.assertTrue(error)
        rollback.os.remove.assert_called_once_with('/home/test/testfile.pdf')
        model.delete.assert_called_once_with()
