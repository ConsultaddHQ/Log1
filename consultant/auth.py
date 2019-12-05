from rest_framework import exceptions

from consultant.models import Consultant, ConsultantToken
from consultant.permissions import get_authorization_header


def user_can_authenticate(consultant):
    """
    Reject users with is_active=False. Custom user models that don't have
    that attribute are allowed.
    """
    is_active = getattr(consultant, 'is_active', None)
    return is_active or is_active is None


def consultant_authenticate(username=None, password=None, **kwargs):
    if username is None:
        username = kwargs.get(Consultant.USERNAME_FIELD)
    try:
        consultant = Consultant._default_manager.get_by_natural_key(username)
    except Consultant.DoesNotExist:
        # Run the default password hasher once to reduce the timing
        # difference between an existing and a nonexistent user (#20760).
        Consultant().set_password(password)
    else:
        return consultant.check_password(password) and user_can_authenticate(consultant)


def get_consultant(request):
    auth = get_authorization_header(request).split()
    key = auth[1].decode()
    try:
        consultant_token = ConsultantToken.objects.select_related('consultant').get(key=key)
    except ConsultantToken.DoesNotExist:
        raise exceptions.AuthenticationFailed('Invalid token.')
    if consultant_token.consultant and consultant_token.consultant.is_authenticated:
        return consultant_token.consultant
