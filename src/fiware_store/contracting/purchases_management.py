import os
import subprocess
from datetime import datetime

from django.conf import settings
from django.template import loader, Context

from charging_engine.charging_engine import ChargingEngine
from fiware_store.models import Purchase
from fiware_store.models import UserProfile
from fiware_store.models import Resource


def create_purchase(user, offering, org_owned=False, tax_address=None):

    if offering.state != 'published':
        raise Exception("This offering can't be purchased")

    profile = UserProfile.objects.get(user=user)

    if offering.pk in profile.offerings_purchased or offering.pk in profile.organization.offerings_purchased:
        raise Exception('The offering has been already purchased')

    #Get the effective tax address
    if tax_address == None:
        tax = profile.tax_address
    else:
        tax = tax_address

    org = ''
    if org_owned == True:
        organization = profile.organization
        org = organization.name
        organization.offerings_purchased.append(offering.pk)
        organization.save()

    # Create the purchase
    purchase = Purchase.objects.create(
        customer=user,
        date=datetime.now(),
        offering=offering,
        owner_organization=org,
        organization_owned=org_owned,
        state='paid',
        tax_address=tax
    )

    # Add the offering to the user profile
    profile.offerings_purchased.append(offering.pk)
    profile.save()

    return purchase
