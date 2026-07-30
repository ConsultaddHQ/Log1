import re


def valid_password(password):
    regex = '^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!#%*?&]{8,}$'
    pattern = re.compile(regex)
    match = re.search(pattern, password)
    if match:
        return True
    else:
        return False
