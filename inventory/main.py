import os
import sys
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import supabase
from inventory.supabase_io import load_json_from_bucket, push_results_to_supabase
from inventory.scraping import get_vendors_information, scrape_vendor_inventory_and_products
from common.retry import with_retry
from models import VendorDirectory, Vendor, VendorInfo
from inventory.diffing import build_vendor_change_logs, build_inventory_logs
from inventory.service import process_vendors, merge_all_products, get_coordinates_of_affected_vendors
from inventory.constants import CONST_SUPABASE_VENDOR_ID_TO_INFO_BUCKET, CONST_SUPABASE_VENDOR_ID_TO_INFO_FP

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
    fetched_at = datetime.now(timezone.utc).isoformat()

    # Fetch old vendor information JSON from Supabase
    logging.info('Starting fetch of vendor information from Supabase')
    try:
        old_vendor_id_to_info = with_retry(
            lambda: load_json_from_bucket(
                client, CONST_SUPABASE_VENDOR_ID_TO_INFO_BUCKET, CONST_SUPABASE_VENDOR_ID_TO_INFO_FP
            ), label=f'load_vendors_information(client)'
        )
    except Exception as e:
        logging.error(
            f'Failed to fetch vendor information from Supabase: {e}'
        )
        sys.exit(
            1
        )

    # Fetch new vendor information JSON from API
    logging.info('Starting fetch of vendor information from API')
    try:
        new_vendor_id_to_info = with_retry(lambda: get_vendors_information(), label='get_vendors_information()')
    except Exception as e:
        logging.error(
            f'Failed to get vendor information: {e}'
        )
        sys.exit(
            1
        )

    # Diff-check inventories
    logging.info('Starting fetch of old vendor inventories from Supabase')
    try:
        old_vendor_directory = VendorDirectory.from_supabase(
            client, old_vendor_id_to_info
        )
    except Exception as e:
        logging.error(f'Old inventories could not be fetched from Supabase: {e}', exc_info=True)
        sys.exit(1)

    logging.info('Starting inventory fetch via API')
    vendor_id_to_offers = {}
    all_pid_to_prod_info = {}
    new_vendor_directory = VendorDirectory()
    for vendor_id, vendor_info in new_vendor_id_to_info.items():
        # TODO: I think checking whether old_inventories.vendors.get(vendor_id) for nullability makes more sense and is more explicit here.
        try:
            filtered_inventory, new_pid_to_info = scrape_vendor_inventory_and_products(vendor_id, vendor_info)
            new_vendor = Vendor(
                vendor_id=vendor_id, info=VendorInfo.from_json(vendor_info), inventory=filtered_inventory
            )
            new_vendor_directory.vendors[vendor_id] = new_vendor
        except Exception as e:
            logging.error(f'Skipping due to failed vendor fetch for vendor ID {vendor_id}: {e}')
            continue

        # TODO: This shouldn't have to be done
        vendor_id_to_offers[vendor_id] = new_vendor.get_inventory_as_dict()

        # Update all_products
        # TODO: This could theoretically be placed outside the for-loop, but that would require to save this redundant information n times (n = num_vendors), no?
        all_pid_to_prod_info = merge_all_products(
            all_pid_to_prod_info, new_pid_to_info
        )

        time.sleep(2.0)

    if new_vendor_directory is None:
        logging.error(f'Failed to fetch any inventory')
        sys.exit(1)

    # Generate logs for changes in vendors' shipping prices or locations
    logging.info('Starting build of vendor change logs')
    vendor_logs = build_vendor_change_logs(
        old_vendor_id_to_info, new_vendor_id_to_info, fetched_at
    )
    logging.info('Starting build of inventory changes logs')
    offer_changes_logs = process_vendors(
        old_vendor_directory, new_vendor_directory, fetched_at
    )
    logging.info('Starting build of offer snapshot logs')
    offer_logs = build_inventory_logs(new_vendor_directory, fetched_at)

    pid_to_vendors = {}
    for vendor_id, offers in vendor_id_to_offers.items():
        for pid, offer in offers.items():
            if pid not in pid_to_vendors:
                pid_to_vendors[pid] = []
            pid_to_vendors[pid].append(
                {
                    'vendor_id': vendor_id,
                    'price': offer['price'],
                    'availability': offer['availability']
                }
            )

    for pid in pid_to_vendors:
        pid_to_vendors[pid].sort(
            key=lambda
                x: x['price']
        )

    updated_vendors_information = get_coordinates_of_affected_vendors(
        vendor_logs, old_vendor_id_to_info, new_vendor_id_to_info
    )

    push_results_to_supabase(
        client,
        offer_changes_logs,
        offer_logs,
        vendor_logs,
        vendor_id_to_offers,
        pid_to_vendors,
        all_pid_to_prod_info,
        updated_vendors_information
    )

    logging.info(f'Terminating script')


if __name__ == '__main__':
    logging.info('Starting script')
    logging.info('Creating Supabase client')
    client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
    run(client)
    logging.info('Terminating script')
