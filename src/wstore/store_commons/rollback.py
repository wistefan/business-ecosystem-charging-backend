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

from __future__ import unicode_literals

import os


def downgrade_asset(self):
    if len(self._to_downgrade.old_versions):
        prev_version = self._to_downgrade.old_versions.pop()
        self._to_downgrade.resource_path = prev_version.resource_path
        self._to_downgrade.version = prev_version.version
        self._to_downgrade.download_link = prev_version.download_link
        self._to_downgrade.meta_info = prev_version.meta_info
        self._to_downgrade.state = 'attached'
        self._to_downgrade.save()


def rollback(post_action=None):
    """
    Make a rollback in case a failure occurs during the execution of a given method
    :param post_action: Callable to be executed as the last step of a rollback
    :return:
    """

    def wrap(method):
        def _remove_file(file_):
            os.remove(file_)

        def _remove_model(model):
            model.delete()

        def wrapper(self, *args, **kwargs):
            # Inject rollback logger
            self.rollback_logger = {
                'files': [],
                'models': []
            }

            try:
                result = method(self, *args, **kwargs)
            except Exception as e:

                # Remove created files
                for file_ in self.rollback_logger['files']:
                    _remove_file(file_)

                # Remove created models
                for model in self.rollback_logger['models']:
                    _remove_model(model)

                if post_action is not None:
                    post_action(self)

                raise e

            return result

        return wrapper
    return wrap
