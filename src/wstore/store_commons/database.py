# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2017 CoNWeT Lab., Universidad Politécnica de Madrid

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


from bson import ObjectId
from pymongo import MongoClient

from django.conf import settings


def get_database_connection():
    """
    Gets a raw database connection to MongoDB
    """
    # Get database info from settings
    database_info = settings.DATABASES['default']

    # Create database connection
    client = None
    if 'CLIENT' in database_info:
        client_info = database_info['CLIENT']

        if 'host' in client_info and 'port' in client_info and 'username' in client_info:
            client = MongoClient(
                client_info['host'],
                int(client_info['port']),
                user=client_info['username'],
                password=client_info['password'])

        elif 'host' in client_info and 'port' in client_info and 'username' not in client_info:
            client = MongoClient(client_info['host'], int(client_info['port']))

        elif 'host' in client_info and 'port' not in client_info and 'username' in client_info:
            client = MongoClient(
                client_info['host'],
                user=client_info['username'],
                password=client_info['password'])

        elif 'host' in client_info and 'port' not in client_info and 'username' not in client_info:
            client = MongoClient(client_info['host'])

        elif 'host' not in client_info and 'port' in client_info and 'username' in client_info:
            client = MongoClient(
                'localhost',
                int(client_info['port']),
                user=client_info['username'],
                password=client_info['password'])

        elif 'host' not in client_info and 'port' in client_info and 'username' not in client_info:
            client = MongoClient('localhost', int(client_info['port']))

        else:
            client = MongoClient()
    else:
        client = MongoClient()

    db_name = database_info['NAME']
    db = client[db_name]

    return db


class DocumentLock:

    def __init__(self, collection, doc_id, lock_id):
        self._collection = collection
        self._doc_id = doc_id
        self._lock_id = '_lock_{}'.format(lock_id)
        self._db = get_database_connection()

    def lock_document(self):
        prev = self._db[self._collection].find_one_and_update(
            {'_id': self._doc_id},
            {'$set': {self._lock_id: True}}
        )
        return self._lock_id in prev and prev[self._lock_id]

    def wait_document(self):
        locked = self.lock_document()

        while locked:
            locked = self.lock_document()

    def unlock_document(self):
        self._db[self._collection].find_one_and_update(
            {'_id': self._doc_id},
            {'$set': {self._lock_id: False}}
        )
