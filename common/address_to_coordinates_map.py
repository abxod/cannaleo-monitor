from geopy.geocoders import Nominatim
import time
import json  # delete after
from common.geo import Coordinate
from geopy.exc import GeocoderTimedOut


def map_address_to_coordinates(
    geolocator,
    street_name_and_house_number: str,
    postalcode: str,
    city: str,
    attempt=1,
    max_attempts=5, ) -> Coordinate | None:
    structured_address = {
        'street': street_name_and_house_number,
        'city': city,
        'country': 'Deutschland',
        'postalcode': postalcode
    }

    try:
        location = geolocator.geocode(structured_address)
    except GeocoderTimedOut:
        if attempt <= max_attempts:
            time.sleep(2)
            return map_address_to_coordinates(
                geolocator, street_name_and_house_number, postalcode, city, attempt=attempt + 1
            )
        raise

    if location is not None:
        latitude = location.latitude
        longitude = location.longitude
        coordinates: Coordinate = {
            'latitude': latitude,
            'longitude': longitude
        }

        return coordinates
    else:
        return None

# if __name__ == '__main__':
#     with open('../scraped_data/vendors/cannaleo_test_updated.json', 'r') as f:
#         vendor_id_to_vendor_info = json.load(f)
#
#     try:
#         with open('../scraped_data/vendors/vendor_id_to_coordinates.json', 'r') as f:
#             vendor_id_to_coordinates = json.load(f)
#     except FileNotFoundError:
#         vendor_id_to_coordinates = {}
#
#     geolocator = Nominatim(
#         user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0',
#         timeout=10
#     )
#
#     for vendor_id, vendor_info in vendor_id_to_vendor_info.items():
#         if vendor_id in vendor_id_to_coordinates:
#             print(f"Skipping already processed vendor: {vendor_id}")
#             continue
#
#         time.sleep(5)
#         street = vendor_info['street']
#         postalcode = vendor_info['plz']
#         city = vendor_info['city']
#
#         try:
#             coordinates = with_retry(lambda: map_address_to_coordinates(geolocator, street, postalcode, city))
#         except Exception as e:
#             print(f"Failed to get coordinates of {vendor_info.get('official_name', vendor_id)}: {e}")
#             with open('../scraped_data/vendors/vendor_id_to_coordinates.json', 'w') as f:
#                 json.dump(vendor_id_to_coordinates, f, indent=2)
#             continue
#
#         if coordinates is None:
#             print(f"Malformed address '{street + ', ' + postalcode + ' ' + city}' could not be found")
#             continue
#
#         vendor_id_to_coordinates[vendor_id] = {
#             'latitude': coordinates[ 'latitude'],
#             'longitude': coordinates['longitude']
#         }
#
#         print(
#             f"Pharmacy at address '{street + ', ' + postalcode + ' ' + city}' is located at {coordinates['latitude']} lat and {coordinates['longitude']} long."
#         )
#
#         # Save after each successful geocode to preserve progress
#         with open('../scraped_data/vendors/vendor_id_to_coordinates.json', 'w') as f:
#             json.dump(
#                 vendor_id_to_coordinates,
#                 f,
#                 indent=2
#                 )
