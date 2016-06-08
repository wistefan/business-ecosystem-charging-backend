# -*- coding: utf-8 -*-

# Copyright (c) 2016 CoNWeT Lab., Universidad Politécnica de Madrid

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

from mock import MagicMock
from nose_parameterized import parameterized

from django.test import TestCase

from wstore.charging_engine import invoice_builder


TEMPLATE = '<html></html>'
USERNAME = 'test-user'
COMPLETE_NAME = 'Test User'

TIMESTAMP = '2016-06-06 10:00:00Z'
OFFERING_NAME = 'Offering'
OFFERING_VERSION = '1.0'

OWNER_NAME = 'owner-user'

BASEDIR = '/home/test'
BILL_ROOT = '/home/test/media/invoices'
MEDIA_URL = '/charging/media/'

TAX = {
    'street': 'street',
    'postal': '12345',
    'province': 'province',
    'city': 'city',
    'country': 'country'
}

SINGLE_MODEL = [{
    'value': '12.00',
    'tax_rate': '20',
    'duty_free': '10.00'
}]

SUBS_MODEL = [{
    'value': '12.00',
    'tax_rate': '20',
    'duty_free': '10.00',
    'unit': 'monthly',
    'renovation_date': unicode(TIMESTAMP)
}]

SINGLE_PAYMENT_TRANS = {
    'currency': 'EUR',
    'related_model': {
        'single_payment': SINGLE_MODEL
    },
    'price': '12.00',
    'duty_free': '10'
}

SUBSCRIPTION_TRANS = {
    'currency': 'EUR',
    'related_model': {
        'subscription': SUBS_MODEL
    },
    'price': '12.00',
    'duty_free': '10'
}

MERGED_TRANS = {
    'currency': 'EUR',
    'related_model': {
        'subscription': SUBS_MODEL,
        'single_payment': SINGLE_MODEL
    },
    'price': '12.00',
    'duty_free': '10'
}

COMMON_CONTEXT = {
    'basedir': BASEDIR,
    'offering_name': OFFERING_NAME,
    'off_organization': OWNER_NAME,
    'off_version': OFFERING_VERSION,
    'ref': '1111',
    'date': TIMESTAMP.split(' ')[0],
    'organization': USERNAME,
    'customer': COMPLETE_NAME,
    'address': TAX['street'],
    'postal': TAX['postal'],
    'city': TAX['city'],
    'province': TAX['province'],
    'country': TAX['country']
}

BASIC_PRICES = {
    'subtotal': '10',
    'tax': '2.00',
    'total': '12.00',
    'cur': 'EUR'
}

SINGLE_PAYMENT_CONTEXT = {
    'exists_single': True,
    'exists_subs': False,
    'single_parts': [('10.00', '20', '12.00', 'EUR')]
}
SINGLE_PAYMENT_CONTEXT.update(COMMON_CONTEXT)
SINGLE_PAYMENT_CONTEXT.update(BASIC_PRICES)

SUBSCRIPTION_CONTEXT = {
    'exists_single': False,
    'exists_subs': True,
    'subs_parts': [('10.00', '20', '12.00', 'EUR', 'monthly', unicode(TIMESTAMP))]
}
SUBSCRIPTION_CONTEXT.update(COMMON_CONTEXT)
SUBSCRIPTION_CONTEXT.update(BASIC_PRICES)

MERGED_CONTEXT = {
    'exists_single': True,
    'exists_subs': True,
    'subs_parts': [('10.00', '20', '12.00', 'EUR', 'monthly', unicode(TIMESTAMP))],
    'single_parts': [('10.00', '20', '12.00', 'EUR')]
}
MERGED_CONTEXT.update(COMMON_CONTEXT)
MERGED_CONTEXT.update(BASIC_PRICES)


class InvoiceBuilderTestCase(TestCase):

    tags = ('invoices',)

    def setUp(self):
        self._order = MagicMock()
        self._order.pk = '1111'
        self._order.tax_address = TAX

        self._order.customer.userprofile.current_organization.name = USERNAME
        self._order.customer.userprofile.complete_name = COMPLETE_NAME

        self._contract = MagicMock()
        self._contract.item_id = '2'
        self._contract.last_charge = TIMESTAMP
        self._contract.offering.name = OFFERING_NAME
        self._contract.offering.version = OFFERING_VERSION
        self._contract.offering.owner_organization.name = OWNER_NAME

        invoice_builder.loader = MagicMock()
        self._template = MagicMock()
        self._template.render.return_value = TEMPLATE
        invoice_builder.loader.get_template.return_value = self._template

        invoice_builder.Context = MagicMock()
        invoice_builder.settings.BILL_ROOT = BILL_ROOT
        invoice_builder.settings.BASEDIR = BASEDIR
        invoice_builder.settings.MEDIA_URL = MEDIA_URL

        invoice_builder.codecs = MagicMock()
        self._file_handler = MagicMock()
        invoice_builder.codecs.open.return_value = self._file_handler

        invoice_builder.os.path.exists = MagicMock()
        invoice_builder.os.path.exists.side_effect = [True, True, False]
        invoice_builder.os.listdir = MagicMock()
        invoice_builder.os.listdir.return_value = ['file1.pdf', 'file1.html']
        invoice_builder.os.remove = MagicMock()

        invoice_builder.subprocess = MagicMock()

    @parameterized.expand([
        ('initial_one_time', 'initial', SINGLE_PAYMENT_TRANS, SINGLE_PAYMENT_CONTEXT),
        ('initial_recurring', 'initial', SUBSCRIPTION_TRANS, SUBSCRIPTION_CONTEXT),
        ('initial_merged', 'initial', MERGED_TRANS, MERGED_CONTEXT)
    ])
    def test_invoice_generation(self, name, concept, transaction, exp_context):

        builder = invoice_builder.InvoiceBuilder(self._order)

        invoice_path = builder.generate_invoice(self._contract, transaction, concept)

        # Validate Path
        invoice_name = self._order.pk + '_' + self._contract.item_id + \
                   '_' + TIMESTAMP.split(' ')[0] + '_2.pdf'

        exp_path = MEDIA_URL + 'bills/' + invoice_name
        html_path = BILL_ROOT + '/' + invoice_name.replace('_2.pdf', '.html')

        self.assertEquals(exp_path, invoice_path)

        # Validate calls
        invoice_builder.loader.get_template.assert_called_once_with('contracting/bill_template_initial.html')
        invoice_builder.Context.assert_called_once_with(exp_context)
        self._template.render.assert_called_once_with(invoice_builder.Context())

        invoice_builder.codecs.open.assert_called_once_with(html_path, 'wb', 'utf-8')
        self._file_handler.write.assert_called_once_with(TEMPLATE)
        self._file_handler.close.assert_called_once_with()

        invoice_builder.subprocess.call.assert_called_once_with([
            BASEDIR + '/create_invoice.sh',
            html_path,
            BILL_ROOT + '/' + invoice_name
        ])

        invoice_builder.os.listdir.assert_called_once_with(BILL_ROOT)
        invoice_builder.os.remove.assert_called_once_with(BILL_ROOT + '/file1.html')
