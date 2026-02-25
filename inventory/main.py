import os
import sys
import logging
import time
from pathlib import Path

import supabase
from inventory.supabase_io import load_vendors_information, push_results_to_supabase
from inventory.scraping import get_vendors_information, scrape_vendor_inventory_and_products
from common.retry import with_retry
from models.models import VendorDirectory
from models.vendor_types import Vendor, VendorInfo
from inventory.diffing import build_vendor_change_logs
from inventory.service import process_vendor, merge_all_products, get_coordinates_of_affected_vendors

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

# TODO: Rename everything to be neutral (product, vendor)
# TODO: The source files are getting really coupled
# TODO: Use 'type' instead of the convoluted 'dict[str, Any]' syntax

SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_KEY']

log_path = Path.cwd() / 'execution_logs.log'

logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

console_handler = logging.StreamHandler(sys.stderr)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(console_handler)

# TODO: Figure out logging
# TODO: The function is getting ugly. Refactor it again

def run(
    client, ):
    # Fetch old vendor information JSON from Supabase
    logging.info('Starting fetch of vendor information from Supabase.')
    try:
        old_vendor_id_to_info = with_retry(
            lambda: load_vendors_information(
                client
            ), None, f'load_vendors_information(client)'
            )
    except Exception as e:
        logging.error(
            f'Failed to fetch vendor information from Supabase: {e}.'
        )
        sys.exit(
            1
        )

    # Fetch new vendor information JSON from API
    logging.info('Starting fetch of vendor information from API')
    try:
        new_vendor_id_to_info = with_retry(lambda: get_vendors_information(), None, 'get_vendors_information()')
    except Exception as e:
        logging.error(
            f'Failed to get vendor information: {e}.'
        )
        sys.exit(
            1
        )

    # Excluded vendor IDs should be removed right here
    logging.info('Starting build of vendor change logs.')
    vendor_logs = build_vendor_change_logs(
        old_vendor_id_to_info, new_vendor_id_to_info
    )

    # Diff-check inventories
    logging.info('Starting fetch of old vendor inventories from Supabase.')
    try:
        old_inventories = VendorDirectory.from_supabase(
            client, old_vendor_id_to_info
        )
    except Exception as e:
        logging.error(f'Old inventories could not be fetched from Supabase: {e}')
        sys.exit(1)
    # TODO: This is actually really stupid. You should scrape in the for loop and not here.
    # TODO: You don't even need a VendorDirectory but just create it at the end of the for loop anyway.
    # TODO: Create a method in Vendor: from_scraping(vendor_info: dict) that populates the inventory

    vendor_inventories = {}
    product_logs = []
    all_pid_to_prod_info = {}
    for vendor_id, vendor_info in new_vendor_id_to_info.items():
        # TODO: I think checking whether old_inventories.vendors.get(vendor_id) for nullability makes more sense and is more explicit here.
        old_vendor = old_inventories.vendors.get(vendor_id)

        try:
            filtered_inventory, new_pid_to_info = scrape_vendor_inventory_and_products(vendor_id, vendor_info)
            new_vendor = Vendor(
                vendor_id=vendor_id, info=VendorInfo.from_json(vendor_info), inventory=filtered_inventory
            )
        except Exception as e:
            # TODO: This should use exponential backoff instead of continuing directly.
            logging.error(f'Skipping due to failed vendor fetch for vendor ID {vendor_id}: {e}')
            continue

        # TODO: Make sure the dict gets unpacked correctly
        # TODO: This shouldn't have to be done, anyway
        vendor_inventories[vendor_id] = new_vendor.get_inventory_as_dict()

        # Update all_products
        all_pid_to_prod_info = merge_all_products(
            all_pid_to_prod_info, new_pid_to_info
        )


        # TODO: if old_vendor is not None?
        if old_vendor is None:
            logging.info(f'Vendor ID {vendor_id} is new. Skipping inventory logs to merging new products.')
            continue


        result = process_vendor(
            int(vendor_id), old_vendor.inventory, new_vendor.inventory
        )

        if result is None:
            continue

        # Add vendor's logs and inventory to collections
        # The assignment seems wrong
        product_logs.extend(
            result
        )

        # Be polite
        time.sleep(2.0)

    updated_vendors_information = get_coordinates_of_affected_vendors(
        vendor_logs, old_vendor_id_to_info, new_vendor_id_to_info
    )

    push_results_to_supabase(
        client, product_logs, vendor_logs, vendor_inventories, all_pid_to_prod_info, updated_vendors_information
    )
    logging.info(f'Terminating script')


if __name__ == '__main__':
    logging.info('Starting script')
    logging.info('Creating Supabase client')
    client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
    run(client)
    logging.info('Terminating script')
