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

from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from wstore.registration.models import Profile


class RegistrationForm(forms.ModelForm):
    """
    """
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    username = forms.RegexField(
        regex=r'^[\w -]{5,}$', max_length=30,
        error_messages={
            'invalid': _("Enter at least 5 characters (letters, digits or"
                         " @/./+/-/_)."),
        })
    email = forms.EmailField(max_length=254)
    password = forms.CharField(
        min_length=5, widget=forms.PasswordInput(),
        error_messages={
            'min_length': _("Enter at least 5 characters."),
        })
    password_check = forms.CharField(
        label=_('Password confirmation'), widget=forms.PasswordInput())
    page = forms.CharField(widget=forms.HiddenInput())

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email')

    def clean_username(self):
        """
        """
        username = self.cleaned_data['username']
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return username
        raise ValidationError("The username is already taken.")

    def clean_email(self):
        """
        """
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email):
            raise ValidationError("The email is already registered.")
        return email

    def clean_password_check(self):
        """
        """
        password1 = self.cleaned_data.get('password')
        password2 = self.cleaned_data['password_check']
        if not password2:
            return password2
        if password1 and password1 == password2:
            return password2
        raise ValidationError("Passwords do not match.")

    def is_valid(self):
        """
        """
        if self.data['page'] == 'login':
            for field in self.fields.values():
                field.required = False
            super(RegistrationForm, self).is_valid()
            return False
        else:
            return super(RegistrationForm, self).is_valid()

    def save(self):
        """
        """
        user = super(RegistrationForm, self).save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.save()
        profile = Profile.objects.create_profile(user)
        return profile.user
