from __future__ import unicode_literals

from rest_framework import exceptions
from consultant.models import ConsultantToken
from rest_framework.permissions import BasePermission
from consultant.authentication import get_authorization_header


class ConsultantIsAuthenticated(BasePermission):
    """
    Allows access only to authenticated Consultants.
    """

    def has_permission(self, request, view):
        auth = get_authorization_header(request).split()
        if len(auth) > 0:
            key = auth[1].decode()
            try:
                consultant_token = ConsultantToken.objects.select_related('consultant').get(key=key)
            except ConsultantToken.DoesNotExist:
                raise exceptions.AuthenticationFailed('Invalid token.')
            if consultant_token.consultant and consultant_token.consultant.is_authenticated:
                return consultant_token.consultant
        else:
            None

