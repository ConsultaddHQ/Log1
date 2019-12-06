from consultant.models import Consultant


def consultant_can_authenticate(consultant):
    """
    Reject consultant with is_active=False.
    """
    is_active = getattr(consultant, 'is_active', None)
    return is_active or is_active is None


def consultant_authenticate(username=None, password=None, **kwargs):
    if username is None:
        username = kwargs.get(Consultant.USERNAME_FIELD)
    try:
        consultant = Consultant._default_manager.get_by_natural_key(username)
    except Consultant.DoesNotExist:
        Consultant().set_password(password)
    else:
        if consultant.check_password(password) and consultant_can_authenticate(consultant):
            return consultant
