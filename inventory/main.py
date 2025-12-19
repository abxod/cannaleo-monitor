import sys
import logging
import time
import supabase
from supabase_io import load_vendors_information, insert_logs_into_db, upload_to_bucket
from scraping import get_vendors_information
from common.retry import with_retry
from models import VendorDirectory
from diffing import build_inventory_change_logs, build_vendor_change_logs
from constants import CONST_SUPABASE_URL, CONST_SUPABASE_KEY
from service import process_vendor, merge_all_products, get_coordinates_of_affected_vendors, intermediately_save_data

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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# TODO: Figure out logging
# TODO: This is a mish-mash of procedural and object-oriented programming
# TODO: The function is getting ugly. Refactor it again.
if __name__ == '__main__':
    client = supabase.create_client(
        CONST_SUPABASE_URL, CONST_SUPABASE_KEY
    )

    logging.info('Starting fetch of vendor information from Supabase.')
    _fetch_start = time.time()
    try:
        old_vendor_id_to_vendor_info = with_retry(
            lambda: load_vendors_information(
                client
            )
        )
        logging.info(f'Successfully fetched vendor information from Supabase in {time.time() - _fetch_start:.2f}s.')
    except Exception as e:
        logging.error(
            f'Failed to fetch vendor information from Supabase: {e}.'
        )
        sys.exit(
            1
        )

    # Diff-check vendors
    logging.info('Starting fetch of vendor information from API')
    _fetch_start = time.time()
    try:
        new_vendor_id_to_vendor_info = with_retry(
            lambda: get_vendors_information()
        )
        logging.info(f'Successfully fetched vendor information from API in {time.time() - _fetch_start:.2f}s.')
    except Exception as e:
        logging.error(
            f'Failed to get vendor information: {e}.'
        )
        sys.exit(
            1
        )

    logging.info('Starting build of vendor change logs.')
    vendor_logs = build_vendor_change_logs(
        old_vendor_id_to_vendor_info, new_vendor_id_to_vendor_info
    ) # TODO: Could this be done in the for loop?

    # Diff-check inventories
    logging.info('Starting fetch of old vendor inventories from Supabase.')
    old_inventories = VendorDirectory.from_supabase(
        client, old_vendor_id_to_vendor_info
    )
    logging.info('Starting fetch of new vendor inventories from API.')
    # TODO: This is actually really stupid. You should scrape in the for loop and not here.
    # TODO: You don't even need a VendorDirectory but just create it at the end of the for loop anyway.
    # TODO: Create a method in Vendor: from_scraping(vendor_info: dict) that populates the inventory
    new_inventories, new_pid_to_info = VendorDirectory.from_scraping(
        new_vendor_id_to_vendor_info
    )

    # For debugging purposes
    intermediately_save_data(new_inventories)

    vendor_inventories = {}
    product_logs = []
    all_pid_to_prod_info = {}
    # TODO: This does not consider that a vendor_id is not in old_inventories.vendors
    for vendor_id, vendor_info in new_vendor_id_to_vendor_info.items():
        old_vendor = old_inventories.vendors.get(str(vendor_id))
        new_vendor = new_inventories.vendors.get(str(vendor_id))

        result = process_vendor(
            str(vendor_id), old_vendor, new_vendor
        )

        if result is None:
            continue

        # Add vendor's logs and inventory to collections
        vendor_product_logs = result
        product_logs.extend(
            vendor_product_logs
        )

        # TODO: Make sure the dict gets unpacked correctly
        # TODO: This shouldn't have to be done, anyway
        vendor_inventories[str(
            vendor_id
        )] = new_vendor.get_inventory_as_dict()

        # TODO: This is wrong because new_inventory only contains price and availability
        # Update all_products
        all_pid_to_prod_info = merge_all_products(
            new_pid_to_info
        )

    updated_vendors_information = get_coordinates_of_affected_vendors(vendor_logs, new_vendor_id_to_vendor_info)

    if product_logs:
        try:
            with_retry(
                lambda: insert_logs_into_db(
                    client, 'product_events', product_logs
                )
            )
        except Exception as e:
            logging.error(
                f'Failed to insert product event logs: {e}.', exc_info=True
            )

    if vendor_logs:
        try:
            with_retry(
                lambda: insert_logs_into_db(client, 'vendor_events', vendor_logs)
            )
        except Exception as e:
            logging.error(
                f'Failed to insert vendor event logs: {e}.', exc_info=True
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
