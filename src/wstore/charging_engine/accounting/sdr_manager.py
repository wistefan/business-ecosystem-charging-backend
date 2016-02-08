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

from datetime import datetime

from django.core.exceptions import PermissionDenied

from wstore.models import Organization, User


class SDRManager(object):

    def __init__(self, user, order, contract):
        self._user = user
        self._order = order
        self._contract = contract
        self._price_model = contract.pricing_model

    def include_sdr(self, sdr):
        # Check that the value field is a valid number
        try:
            float(sdr['value'])
        except:
            raise ValueError('The provided value is not a valid number')

        # Check that the customer exist
        customer = Organization.objects.filter(name=sdr['customer'])

        if not len(customer):
            raise ValueError('The specified customer ' + sdr['customer'] + ' does not exist')

        # Check if the user making the request belongs to the customer organization
        belongs = False
        for org in self._user.userprofile.organizations:
            if org['organization'] == self._order.owner_organization.pk:
                belongs = True
                break

        if not belongs:
            raise PermissionDenied("You don't belong to the customer organization")

        if 'pay_per_use' not in self._price_model:
            raise ValueError('The pricing model of the offering does not define pay-per-use components')

        # Check the correlation number and timestamp
        applied_sdrs = self._contract.applied_sdrs
        pending_sdrs = self._contract.pending_sdrs

        last_corr = 0
        last_time = None

        if len(pending_sdrs) > 0:
            last_corr = int(pending_sdrs[-1]['correlationNumber'])
            last_time = pending_sdrs[-1]['timestamp']
        elif len(applied_sdrs) > 0:
            last_corr = int(applied_sdrs[-1]['correlationNumber'])
            last_time = applied_sdrs[-1]['timestamp']

        # Truncate ms to 3 decimals (database supported)
        sp_time = sdr['timestamp'].split('.')
        milis = sp_time[1]

        if len(milis) > 3:
            milis = milis[:3]

        sdr_time = sp_time[0] + '.' + milis

        try:
            time_stamp = datetime.strptime(sdr_time, '%Y-%m-%dT%H:%M:%S.%f')
        except:
            time_stamp = datetime.strptime(sdr_time, '%Y-%m-%d %H:%M:%S.%f')

        if int(sdr['correlationNumber']) != last_corr + 1:
            raise ValueError('Invalid correlation number, expected: ' + str(last_corr + 1))

        if last_time is not None and last_time > time_stamp:
            raise ValueError('The provided timestamp specifies a lower timing than the last SDR received')

        # Check that the pricing model contains the specified unit
        found_model = False
        for comp in self._price_model['pay_per_use']:
            if sdr['unit'] == comp['unit']:
                found_model = True
                break

        if not found_model:
            raise ValueError('The specified unit is not included in the pricing model')

        # Store the SDR
        sdr['timestamp'] = time_stamp
        self._contract.pending_sdrs.append(sdr)
        self._order.save()
