from __future__ import unicode_literals
from rest_framework import exceptions
from django.utils.translation import ugettext_lazy as _
from rest_framework.authentication import get_authorization_header

from consultant.models import ConsultantToken


class ConsultantTokenAuthentication(object):
    """
    Simple token based authentication.

    Clients should authenticate by passing the token key in the "Authorization"
    HTTP header, prepended with the string "Token ".  For example:

        Authorization: Token 401f7ac837da42b97f613d789819ff93537bee6a
    """

    keyword = 'Token'
    model = None

    def get_model(self):
        if self.model is not None:
            return self.model
        from consultant.models import ConsultantToken
        return ConsultantToken

    """
    A custom token model may be used, but must have the following properties.

    * key -- The string identifying the token
    * user -- The user to which the token belongs
    """

    def authenticate(self, request):
        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            msg = _('Invalid token header. No credentials provided.')
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _('Invalid token header. Token string should not contain spaces.')
            raise exceptions.AuthenticationFailed(msg)

        try:
            token = auth[1].decode()
        except UnicodeError:
            msg = _('Invalid token header. Token string should not contain invalid characters.')
            raise exceptions.AuthenticationFailed(msg)

        return self.authenticate_credentials(token)

    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            token = model.objects.select_related('consultant').get(key=key)
        except model.DoesNotExist:
            raise exceptions.AuthenticationFailed(_('Invalid token.'))

        if not token.consultant.is_active:
            raise exceptions.AuthenticationFailed(_('Consultant is inactive or deleted.'))

        return (token.consultant, token)

    def authenticate_header(self, request):
        return self.keyword


def get_consultant(request):
    auth = get_authorization_header(request).split()
    key = auth[1].decode()
    try:
        consultant_token = ConsultantToken.objects.select_related('consultant').get(key=key)
    except ConsultantToken.DoesNotExist:
        raise exceptions.AuthenticationFailed('Invalid token.')
    if consultant_token.consultant and consultant_token.consultant.is_authenticated:
        return consultant_token.consultant
