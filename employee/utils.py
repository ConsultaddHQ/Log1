import re


def valid_password(password):
    regex = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!#%*?&]{8,}$"
    pattern = re.compile(regex)
    match = re.search(pattern, password)
    if match:
        return True, 'valid'
    else:
        invalid_conditions = ''

        if len(password) < 8:
            invalid_conditions += "Password must have at least 8 characters. "

        if password.isnumeric():
            invalid_conditions += "Password can not be entirely numeric. "

        if not re.search(r'[a-z]', password):
            invalid_conditions += "Password must have at least one lowercase letter. "

        if not re.search(r'[A-Z]', password):
            invalid_conditions += "Password must have at least one uppercase letter. "

        if not re.search(r'\d', password):
            invalid_conditions += "Password must have at least one digit. "

        if not re.search(r'[@$!%*#?&]', password):
            invalid_conditions += "Password must have at least one special character (@$!%*#?&). "

        return False, invalid_conditions
