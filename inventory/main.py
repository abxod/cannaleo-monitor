import sys
import logging
import time
import supabase
from geopy.geocoders import Nominatim
import events
from supabase_io import load_vendors_information, insert_logs_into_db, upload_to_bucket
from service import process_vendor
from scraping import get_vendors_information
from common.retry import with_retry
from models import VendorDirectory
from diffing import build_inventory_change_logs, build_vendor_change_logs
from common.address_to_coordinates_map import map_address_to_coordinates
from common.geo import Coordinate
from constants import CONST_SUPABASE_URL, CONST_SUPABASE_KEY, CONST_ALL_VENDOR_IDS, CONST_VENDOR_EVENT_TYPES_FOR_UPDATES


"""
    This source file is responsible for updating:
        1. the vendor inventories,
        2. the current vendors supported by Cannaleo.
        3. and a file containing information pertaining to every strain currently in every vendor's inventory.
    and inserting:
        1. any changes in the price or availability of a product in any vendor's inventory
        2. and any addition, removal, or change in price in any vendor's shipping options and location changes
    on Supabase.
"""


# TODO: Figure out logging
# TODO: This is a mish-mash of procedural and object-oriented programming
# TODO: The function is getting ugly. Refactor it again.
if __name__ == '__main__':
    client = supabase.create_client(
        CONST_SUPABASE_URL, CONST_SUPABASE_KEY
    )

    try:
        old_vendor_id_to_vendor_info = with_retry(
            lambda: load_vendors_information(
                client
            )
        )
    except Exception as e:
        logging.error(
            f'Failed to fetch vendor information from Supabase: {e}'
        )
        sys.exit(
            1
        )

    # Diff-check vendors
    try:
        new_vendor_id_to_vendor_info = with_retry(
            lambda: get_vendors_information()
        )
    except Exception as e:
        logging.error(
            f'Failed to get vendor information: {e}'
        )
        sys.exit(
            1
        )

    vendor_logs = build_vendor_change_logs(
        old_vendor_id_to_vendor_info, new_vendor_id_to_vendor_info
    )

    # Diff-check inventories
    old_inventories = VendorDirectory.from_supabase(
        client, old_vendor_id_to_vendor_info
    )
    new_inventories = VendorDirectory.from_scraping(
        new_vendor_id_to_vendor_info
    )

    vendor_inventories = {}
    product_logs = []
    all_pid_to_prod_info = {}
    seen_strains = set()
    # TODO: This does not consider that a vendor_id is not in old_inventories.vendors
    for vendor_id, vendor_info in new_vendor_id_to_vendor_info.items():
        if vendor_id not in old_inventories.vendors.keys():
            pass

        old_vendor = old_inventories.vendors.get('vendor_id')
        new_vendor = new_inventories.vendors.get('vendor_id')

        result = process_vendor(
            old_vendor, new_vendor
        )

        if result is None:
            continue

        # Add vendor's logs and inventory to collections
        vendor_product_logs= result
        product_logs.extend(
            vendor_product_logs
        )

        # TODO: Make sure the dict gets unpacked correctly
        vendor_inventories[str(
            vendor_id
        )] = new_vendor.get_inventory_as_dict()

        # TODO: This is wrong because new_inventory only contains price and availability
        # Update all_products
        all_pid_to_prod_info = merge_all_products(new_inventory)
        # for pid, prod_info in new_inventory.items():
        #     if pid not in seen_strains:
        #         seen_strains.add(pid)
        #         all_pid_to_prod_info[pid] = prod_info

    updated_vendors_information = {}

    vendor_added_or_location_logs = [log for log in vendor_logs if log[
        'event_type'] in CONST_VENDOR_EVENT_TYPES_FOR_UPDATES]
    vendor_ids_added_or_location = {log['vendor_id'] for log in
                                    vendor_added_or_location_logs}  # Vendor IDs whose coordinates need to be calculated
    spatially_unaffected_vendor_ids = new_vendor_id_to_vendor_info.keys() - vendor_ids_added_or_location  # Vendor IDs whose coordinates do not need to be calculated
    for vendor_id in spatially_unaffected_vendor_ids:
        updated_vendors_information[vendor_id] = new_vendor_id_to_vendor_info[vendor_id]

    if len(vendor_added_or_location_logs) != 0:
        geolocator = Nominatim(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0',
            timeout=10
        )

        for vendor_id in vendor_ids_added_or_location:
            street = new_vendor_id_to_vendor_info[vendor_id]['street']
            postalcode = new_vendor_id_to_vendor_info[vendor_id]['plz']
            city = new_vendor_id_to_vendor_info[vendor_id]['city']

            try:
                time.sleep(1)
                coordinates = map_address_to_coordinates(geolocator, street, postalcode, city)
            except Exception as e:
                logging.error(
                    f'Failed to get coordinates of {new_vendor_id_to_vendor_info[vendor_id].get('official_name', vendor_id)}: {e}'
                )
                continue

            if coordinates is None:
                logging.warning(f'Malformed address \'{street + ', ' + postalcode + ' ' + city}\' could not be found.')
                coordinates = Coordinate(latitude=0, longitude=0)

            updated_vendors_information[vendor_id] = {
                **new_vendor_id_to_vendor_info[vendor_id],
                'latitude': coordinates.get('latitude'),
                'longitude': coordinates.get('longitude')
            }

    if product_logs:
        try:
            with_retry(
                lambda: insert_logs_into_db(
                    client, 'product_events', product_logs
                )
            )
        except Exception as e:
            logging.error(
                f'Failed to insert product event logs: {e}', exc_info=True
            )

    if vendor_logs:
        try:
            with_retry(
                lambda: insert_logs_into_db(client, 'vendor_events', vendor_logs)
            )
        except Exception as e:
            logging.error(
                f'Failed to insert vendor event logs: {e}', exc_info=True
            )

    if vendor_inventories:
        try:
            with_retry(
                lambda: upload_to_bucket(
                    client, 'inventories_bucket', 'vendors_inventories.json', vendor_inventories
                    )
            )
        except Exception as e:
            logging.error(
                f'Failed to upload vendor inventories: {e}', exc_info=True
            )

    if all_pid_to_prod_info:
        try:
            with_retry(
                lambda: upload_to_bucket(
                    client, 'all_products_bucket', 'all_current_products.json', all_pid_to_prod_info
                )
            )
        except Exception as e:
            logging.error(f'Failed to upload all products: {e}', exc_info=True)

    if updated_vendors_information:
        try:
            with_retry(
                lambda: upload_to_bucket(
                    client, 'vendors_info_bucket', 'vendors_information.json', updated_vendors_information
                )
            )
        except Exception as e:
            logging.error(
                f'Failed to update vendors\' information: {e}', exc_info=True
            )
