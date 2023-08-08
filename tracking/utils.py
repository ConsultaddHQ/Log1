import time
import uuid
import string
import random
from geopy.geocoders import Nominatim

app = Nominatim(user_agent="log1 location")


def get_address_by_location(latitude, longitude, language="en"):
    """This function returns an address as raw from a location
    will repeat until success"""
    coordinates = f"{latitude}, {longitude}"
    time.sleep(1)
    try:
        return app.reverse(coordinates, language=language).raw
    except:
        return get_address_by_location(latitude, longitude)


def generate_unique_cookies():
    unique_id = str(uuid.uuid4().hex)
    random_string = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
    cookies = unique_id[:10] + random_string
    return cookies


def string_to_decimal_point_converter(input_string):
    two_digit_float = float(input_string)
    two_digit_float = round(two_digit_float, 2)
    return str(two_digit_float)
