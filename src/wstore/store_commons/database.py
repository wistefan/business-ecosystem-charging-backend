# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2016 CoNWeT Lab., Universidad Politécnica de Madrid

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

from pymongo import MongoClient

from django.conf import settings


def get_database_connection():
    """
    Gets a raw database connection to MongoDB
    """
    # Get database info from settings
    database_info = settings.DATABASES['default']

    client = None
    # Create database connection
    if database_info['HOST'] and database_info['PORT']:
        client = MongoClient(database_info['HOST'], database_info['PORT'])
    elif database_info['HOST'] and not database_info['PORT']:
        client = MongoClient(database_info['HOST'])
    elif not database_info['HOST'] and database_info['PORT']:
        client = MongoClient('localhost', database_info['PORT'])
    else:
        client = MongoClient()


    db_name = database_info['NAME']
    db = client[db_name]

    #Authenticate if needed
    if database_info['USER'] and database_info['PASSWORD']:
        db.authenticate(database_info['USER'], database_info['PASSWORD'], mechanism='MONGODB-CR')

    return db
