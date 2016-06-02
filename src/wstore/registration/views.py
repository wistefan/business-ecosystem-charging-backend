# -*- coding: utf-8 -*-

# Copyright (c) 2013 CoNWeT Lab., Universidad Politécnica de Madrid

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

from django.contrib import messages
from django.contrib.auth import login
from django.http import HttpResponseNotFound
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_http_methods
from django.views.generic.edit import FormView

from wstore.registration.forms import RegistrationForm
from wstore.registration.models import Profile


class RegistrationView(FormView):
    """
    """
    http_method_names = ['head', 'get', 'post']
    template_name = 'registration/signup_template.html'
    form_class = RegistrationForm

    def form_valid(self, form):
        """
        """
        new_user = form.save()
        self.create_success_message(new_user)
        return self.render_to_response(
            self.get_context_data(form=form, success=True))

    def create_success_message(self, user):
        """
        """
        message = _("WStore has sent an activation e-mail to %s."
                    "Please, check it out.") % (user.email)
        messages.success(self.request, message)


signup_view = RegistrationView.as_view()


@require_http_methods(["GET"])
def activate_view(request, activation_key):
    """
    """
    user = Profile.objects.activate_user(activation_key)
    if user:
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        message = _("Well done! You can use WStore.")
        messages.success(request, message)
        return redirect('home')
    return HttpResponseNotFound('<h1>Page not found</h1>')
