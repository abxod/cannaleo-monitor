from math import radians, cos, sin, asin, sqrt

def haversine(own_longitude, own_latitude, vendor_longitude, vendor_latitude):
    """
    Calculate the great circle distance in kilometers between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    own_longitude, own_latitude, vendor_longitude, vendor_latitude = map(radians, [own_longitude, own_latitude, vendor_longitude, vendor_latitude])

    # haversine formula
    dlon = vendor_longitude - own_longitude
    dlat = vendor_latitude - own_latitude
    a = sin(dlat/2) ** 2 + cos(own_latitude) * cos(vendor_latitude) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles. Determines return value units.
    return c * r