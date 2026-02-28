import time
import logging
from geopy.geocoders import Nominatim

from models.models import ProductOffer
from models import Coordinate
from inventory.diffing import build_inventory_change_logs
from inventory.constants import CONST_VENDOR_EVENT_TYPES_FOR_UPDATES, CONST_EXCLUDED_VENDOR_IDS
from common.address_to_coordinates_map import map_address_to_coordinates
from models import VendorDirectory

# TODO: When does it make sense to pass old, new as a tuple together?
"""
Build product offer logs.
Any changes observed in the price or availability status between old and new offers are turned into logs to be pushed to Supabase.
"""


# TODO: Either the name is bad or this function is just redundant as fuck. I'm thinking the former.
def process_vendors(
    old_vendor_directory: VendorDirectory,
    new_vendor_directory: VendorDirectory,
    fetched_at, ):
    old_vendors = old_vendor_directory.vendors
    new_vendors = new_vendor_directory.vendors

    offer_changes_logs = []
    for vendor_id, vendor in new_vendors.items():
        if old_vendors.get(vendor_id) is None:
            logging.info(f'Vendor ID {vendor_id} is new. Skipping building inventory logs')
            continue

        old_vendor_inventory = old_vendors[vendor_id].inventory
        new_vendor_inventory = new_vendors[vendor_id].inventory

        if old_vendor_inventory == new_vendor_inventory:
            logging.info(f'No inventory changes observed for {vendor_id}')
            continue

        logs = build_inventory_change_logs(
            int(vendor_id), old_vendor_inventory, new_vendor_inventory, fetched_at
        )
        offer_changes_logs.extend(logs)

    return offer_changes_logs


def merge_all_products(
    all_pid_to_prod_info: dict,
    new_pid_to_info: dict, ):
    for pid, prod_info in all_pid_to_prod_info.items():
        if pid in new_pid_to_info:
            continue

        new_pid_to_info[pid] = prod_info
    return new_pid_to_info


# TODO: This can be refactored further
def get_coordinates_of_affected_vendors(
    vendor_logs: list,
    old_vendor_id_to_info: dict,
    new_vendor_id_to_info: dict, ) -> dict:
    updated_vendor_id_to_info = {}

    vendor_added_or_location_logs = [log for log in vendor_logs if log[
        'event_type'] in CONST_VENDOR_EVENT_TYPES_FOR_UPDATES]  # Vendor IDs whose coordinates need to be fetched

    vendor_ids_added_or_location = {log['vendor_id'] for log in
                                    vendor_added_or_location_logs}  # previously: - CONST_EXCLUDED_VENDOR_IDS. Not sure if this is still needed after removing the excluded vendors during fetch

    spatially_unaffected_vendor_ids = new_vendor_id_to_info.keys() - vendor_ids_added_or_location - CONST_EXCLUDED_VENDOR_IDS  # Vendor IDs whose coordinates do not need to be fetched

    updated_vendor_id_to_info = {vendor_id: {
        **new_vendor_id_to_info[vendor_id], **({
                                                   'latitude': old_vendor_id_to_info[vendor_id].get('latitude'),
                                                   'longitude': old_vendor_id_to_info[vendor_id].get('longitude'),
                                               } if vendor_id in old_vendor_id_to_info else {})
    } for vendor_id in spatially_unaffected_vendor_ids}

    # TODO: This can be continue'd
    if len(vendor_ids_added_or_location) != 0:
        geolocator = Nominatim(
            user_agent='homeless-vendor-geocoder/1.0 aboodcr@outlook.com',
            timeout=10
        )

        for vendor_id in vendor_ids_added_or_location:
            if vendor_id in CONST_EXCLUDED_VENDOR_IDS:
                continue

            street = new_vendor_id_to_info[vendor_id].get('street')
            postalcode = new_vendor_id_to_info[vendor_id].get('plz')
            city = new_vendor_id_to_info[vendor_id].get('city')

            if not all([street, postalcode, city]):
                logging.warning(f'Incomplete address for vendor {vendor_id}')
                continue

            try:
                time.sleep(5)
                coordinates = map_address_to_coordinates(geolocator, street, postalcode, city)
            except Exception as e:
                logging.error(
                    f'Failed to get coordinates of {new_vendor_id_to_info[vendor_id].get('official_name', vendor_id)}: {e}'
                )
                continue

            if coordinates is None:
                logging.warning(
                    f'Malformed address \'{street + ', ' + postalcode + ' ' + city}\' for vendor ID {vendor_id} could not be found.'
                )
                coordinates: Coordinate = {
                    'latitude': 0,
                    'longitude': 0
                }

            updated_vendor_id_to_info[vendor_id] = {
                **new_vendor_id_to_info[vendor_id],
                'latitude': coordinates.get('latitude'),
                'longitude': coordinates.get('longitude')
            }

    return updated_vendor_id_to_info
