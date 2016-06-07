# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2016 CoNWeT Lab., Universidad Politécnica de Madrid

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

import time

from datetime import datetime

from django.core.management.base import BaseCommand

from wstore.charging_engine.charging_engine import ChargingEngine
from wstore.models import Organization


class Command(BaseCommand):

    def resolve_purchase_usage(self, purchase):
        # Get payment info
        if purchase.organization_owned:
            org = purchase.owner_organization
            payment_info = org.payment_info
        else:
            payment_info = purchase.customer.userprofile.payment_info

        charging = ChargingEngine(purchase, payment_method='credit_card', credit_card=payment_info)
        charging.resolve_charging(type_='use')

    def handle(self, *args, **options):
        """
            This method is used to perform the charging process
            of the asset_manager that have pending SDR for more than
            a month
        """
        now = time.mktime(datetime.utcnow().timetuple())

        if len(args) == 0:
            # Get contracts
            for contract in Contract.objects.all():

                pending_sdrs = contract.pending_sdrs

                # If there are subscriptions the renovations are used as triggers
                if len(pending_sdrs) > 0 and (not 'subscription' in contract.pricing_model):
                    time_stamp = time.mktime(pending_sdrs[0]['time_stamp'].timetuple())

                    if (time_stamp + 2592000) <= now:  # A month
                        # Get the related payment info
                        self.resolve_purchase_usage(contract.purchase)

        elif len(args) == 1:
            # Get the purchase
            try:
                purchase = Purchase.objects.get(ref=args[0])
            except:
                raise Exception('The provided purchase does not exists')

            # Get the contract
            contract = purchase.contract

            # Check if there are pending SDRs
            if len(contract.pending_sdrs) > 0:
                self.resolve_purchase_usage(purchase)
            else:
                raise Exception('No accounting info in the provided purchase')
        else:
            raise Exception('Invalid number of arguments')
