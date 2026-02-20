import sys
import logging
import time
import supabase
from supabase_io import load_vendors_information, insert_logs_into_db, upload_to_bucket
from scraping import get_vendors_information, scrape_vendor_inventory_and_products
from common.retry import with_retry
from models import VendorDirectory
from vendor_types import Vendor, VendorInfo, ShippingOptions, ProductOffer
from diffing import build_inventory_change_logs, build_vendor_change_logs
from constants import CONST_SUPABASE_URL, CONST_SUPABASE_KEY, CONST_EXCLUDED_VENDOR_IDS
from service import process_vendor, merge_all_products, get_coordinates_of_affected_vendors

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

# TODO: The source files are getting really coupled
# TODO: Use 'type' instead of the convoluted 'dict[str, Any]' syntax

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# TODO: Figure out logging
# TODO: This is a mish-mash of procedural and object-oriented programming
# TODO: The function is getting ugly. Refactor it again
if __name__ == '__main__':
    logging.info('Starting program')

    client = supabase.create_client(
        CONST_SUPABASE_URL, CONST_SUPABASE_KEY
    )

    logging.info('Starting fetch of vendor information from Supabase.')
    try:
        old_vendor_id_to_info = with_retry(
            lambda: load_vendors_information(
                client
            )
        )
    except Exception as e:
        logging.error(
            f'Failed to fetch vendor information from Supabase: {e}.'
        )
        sys.exit(
            1
        )

    # Diff-check vendors
    logging.info('Starting fetch of vendor information from API')
    try:
        new_vendor_id_to_info = with_retry(
            lambda: get_vendors_information()
        )
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
    old_inventories = VendorDirectory.from_supabase(
        client, old_vendor_id_to_info
    )
    # TODO: This is actually really stupid. You should scrape in the for loop and not here.
    # TODO: You don't even need a VendorDirectory but just create it at the end of the for loop anyway.
    # TODO: Create a method in Vendor: from_scraping(vendor_info: dict) that populates the inventory

    vendor_inventories = {}
    product_logs = []
    all_pid_to_prod_info = {}
    for vendor_id, vendor_info in new_vendor_id_to_info.items():
        if vendor_id in CONST_EXCLUDED_VENDOR_IDS:
            continue

        # TODO: I think checking whether old_inventories.vendors.get(vendor_id) for nullability makes more sense and is more explicit here.
        old_vendor = old_inventories.vendors.get(str(vendor_id))

        # TODO: if old_vendor is not None?
        if old_vendor is None:
            logging.info(f'Vendor is new. Skipping inventory logs to merging new products.')
            continue
        else:
            try:
                # Returns
                # TODO: filtered_inventory is not a dict of ProductOffers.
                filtered_inventory, new_pid_to_info = scrape_vendor_inventory_and_products(vendor_id, vendor_info)
                new_vendor = Vendor(vendor_id=vendor_id, info=VendorInfo.from_json(vendor_info), inventory=filtered_inventory)
                # new_vendor = Vendor.from_scraping(vendor_id, vendor_info)
            except Exception as e:
                # TODO: This should use exponential backoff instead of continuing directly.
                logging.error(f'{e}: Skipping due to failed vendor fetch for vendor ID {vendor_id}.')
                continue

            result = process_vendor(
                str(vendor_id), old_vendor.inventory, new_vendor.inventory
            )

            if result is None:
                continue

            # Add vendor's logs and inventory to collections
            # The assignment seems wrong
            product_logs.extend(
                result
            )

            # TODO: Make sure the dict gets unpacked correctly
            # TODO: This shouldn't have to be done, anyway
            vendor_inventories[vendor_id] = new_vendor.get_inventory_as_dict()

        # Update all_products
        all_pid_to_prod_info = merge_all_products(
            all_pid_to_prod_info,
            new_pid_to_info
        )

        # Be polite
        time.sleep(1)

    updated_vendors_information = get_coordinates_of_affected_vendors(vendor_logs, old_vendor_id_to_info, new_vendor_id_to_info)

    logging.info('Pushing product logs to Supabase.')
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

    logging.info('Pushing vendor logs to Supabase.')
    if vendor_logs:
        try:
            with_retry(
                lambda: insert_logs_into_db(client, 'vendor_events', vendor_logs)
            )
        except Exception as e:
            logging.error(
                f'Failed to insert vendor event logs: {e}.', exc_info=True
            )

    logging.info('Updating vendor_inventories.json on Supabase.')
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

    logging.info('Updating all_products.json on Supabase.')
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