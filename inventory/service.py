import time
import logging
from typing import Any
from geopy.geocoders import Nominatim

from inventory.models import Vendor
from common.geo import Coordinate
from diffing import build_inventory_change_logs
from constants import CONST_VENDOR_EVENT_TYPES_FOR_UPDATES
from common.address_to_coordinates_map import map_address_to_coordinates

import datetime
import json
from models import VendorDirectory

def process_vendor(
    vendor_id: str,
    old_vendor: Vendor,
    new_vendor: Vendor, ) -> list | None:

    if old_vendor is None or new_vendor is None:
        logging.info(f'Vendor ID {vendor_id} is no. No product logs need to be created')

    new_inventory = new_vendor.inventory
    old_inventory = old_vendor.inventory

    if new_inventory == old_inventory:
        logging.info(f'No inventory changes observed for {vendor_id}.')
        return None

    logging.info(f'Building inventory change logs for vendor ID {vendor_id}.')
    logs = build_inventory_change_logs(
        int(vendor_id), new_inventory, old_inventory, )

    return logs


def merge_all_products(
    new_pid_to_info: dict, ):
    seen_strains = set()

    all_pid_to_prod_info = {}
    for pid, prod_info in new_pid_to_info.items():
        if pid in seen_strains:
            continue

        all_pid_to_prod_info[pid] = prod_info

    return all_pid_to_prod_info


# TODO: This can be refactored further
def get_coordinates_of_affected_vendors(
    vendor_logs: list,
    new_vendor_id_to_info: dict, ) -> dict:
    updated_vendor_id_to_info = {}

    vendor_added_or_location_logs = [log for log in vendor_logs if log[
        'event_type'] in CONST_VENDOR_EVENT_TYPES_FOR_UPDATES]  # Vendor IDs whose coordinates need to be fetched

    vendor_ids_added_or_location = {log['vendor_id'] for log in vendor_added_or_location_logs}

    spatially_unaffected_vendor_ids = new_vendor_id_to_info.keys() - vendor_ids_added_or_location  # Vendor IDs whose coordinates do not need to be fetched

    for vendor_id in spatially_unaffected_vendor_ids:
        updated_vendor_id_to_info[vendor_id] = new_vendor_id_to_info[vendor_id]

    # TODO: This can be continue'd
    if len(vendor_added_or_location_logs) != 0:
        geolocator = Nominatim(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0',
            timeout=10
            )

        for vendor_id in vendor_ids_added_or_location:
            street = new_vendor_id_to_info[vendor_id]['street']
            postalcode = new_vendor_id_to_info[vendor_id]['plz']
            city = new_vendor_id_to_info[vendor_id]['city']

            try:
                time.sleep(5)
                coordinates = map_address_to_coordinates(geolocator, street, postalcode, city)
            except Exception as e:
                logging.error(f'Failed to get coordinates of {new_vendor_id_to_info[vendor_id].get('official_name', vendor_id)}: {e}')
                continue

            if coordinates is None:
                logging.warning(f'Malformed address \'{street + ', ' + postalcode + ' ' + city}\' could not be found.')
                coordinates = Coordinate(latitude=0, longitude=0)

            updated_vendor_id_to_info[vendor_id] = {
                **new_vendor_id_to_info[vendor_id],
                'latitude': coordinates.get('latitude'),
                'longitude': coordinates.get('longitude')
            }

    return updated_vendor_id_to_info

# TODO: Should this function be temporary?
def intermediately_save_data(new_inventories: VendorDirectory):
    new_inventories_dict = new_inventories.vendors

    dumpable_inventories = {}
    for vendor_id, vendor_obj in new_inventories_dict.items():
        dumpable_inventories[vendor_id] = vendor_obj.get_inventory_as_dict()

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
    file_path = f'../data/all_inventories{timestamp}'

    with open(file_path, 'w') as f:
        json.dump(dumpable_inventories, f, indent=2)

    logging.info(f'Saved inventories to {file_path}')