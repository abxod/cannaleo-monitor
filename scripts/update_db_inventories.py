import time
import logging
import json  # I don't like that json is being imported here. Import a method from functions.py that handles that
import supabase
from functions import scrape_filtered_vendor_inventory, read_vendor_inventory_db, upload_vendors_inventories, \
    insert_logs_into_db
from inventory.events import log_product
from inventory.constants import *
# from classes import ModifiedStrain

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='inventory_update.log'
)

# TODO: Separate logic from IO
# TODO: This script should be a directory that contains main.py (a single line calling a function), and script files that define/import the required functions (from another directory)
# TODO: This script should also log new vendors in vendor_events
# No use case for this comes to mind just this. -> Maybe a price tracker
if __name__ == '__main__':
    supabase_client = supabase.create_client(CONST_SUPABASE_URL, CONST_SUPABASE_KEY)

    vendor_id_to_information = {}
    # TODO: Wrap this in a try catch (Exception) block with exponential backoff
    response = supabase_client.storage.from_('static_information').download('cannaleo_vendors_information.json', )

    # TODO: Read the vendors' inventories file here

    # File's contents are fetched in raw bytes, so convert to str
    json_str = response.decode(encoding='utf-8')
    if json_str:
        vendor_id_to_information = json.loads(json_str)

    vendor_ids = CONST_ALL_VENDOR_IDS
    vendor_inventories = {}
    for vendor_id in vendor_ids:
        time.sleep(1)  # Don't disrupt service

        # TODO: It might be wise to fetch the JSON file not in scrape_filtered_vendor_inventory(), but here, so that upload_vendor_inventory() doesn't have to call json.dumps on it.

        try:
            vendor_domain = vendor_id_to_information[str(vendor_id)]['domain']
            now = time.time()
        except KeyError:
            logging.warning(f'Vendor ID {vendor_id} missing in vendor info JSON.')
            continue

        # new_inventory refers to both entirely new strains and strains that were previously not in stock\
        # TODO: When a new vendor comes in, their PID will not be in old_inventory. Implement execution path.
        new_inventory = scrape_filtered_vendor_inventory(vendor_id=vendor_id, vendor_domain=vendor_domain,
                                                         attributes={'price', 'availibility'})
        old_inventory = read_vendor_inventory_db(vendor_id=vendor_id, conn=supabase_client)

        # TODO: Is this error handling correctly implemented?
        if not old_inventory:
            logging.warning(f'Old inventory missing in DB for vendor {vendor_id}. Skipping.')
            continue

        # No changes in the inventory observed -> nothing to do.
        if new_inventory == old_inventory:
            print(f'No inventory changes observed for {vendor_domain}.')
            continue

        new_inventory_pids = set(new_inventory.keys())
        old_inventory_pids = set(old_inventory.keys())

        # Log events where a strain has been added or removed
        product_events_logs_to_insert = []
        added_pids = new_inventory_pids - old_inventory_pids
        removed_pids = old_inventory_pids - new_inventory_pids

        if len(added_pids) != 0:
            for pid in added_pids:
                product_events_logs_to_insert.append(log_product(vendor_id, pid, 'added'))

        if len(removed_pids) != 0:
            for pid in removed_pids:
                product_events_logs_to_insert.append(log_product(vendor_id, pid, 'removed'))

        # Log events where a strain's availability or price has changed
        shared_pids = new_inventory_pids.intersection(old_inventory_pids)
        modified_strains = {pid: {
            'old': old_inventory[pid],
            'new': new_inventory[pid]
        } for pid in shared_pids}

        for pid, old_new_values in modified_strains.items():
            old_availability = old_new_values['old']['availability']
            new_availability = new_inventory[pid]['availability']

            if old_availability != old_new_values['new']['avail']:
                product_events_logs_to_insert.append(log_product(vendor_id, pid, 'availability', old_avail=old_availability, new_avail=new_availability))

            old_price = old_new_values['old']['price']
            new_price = old_new_values['new']['price']

            if old_price != new_price:
                product_events_logs_to_insert.append(log_product(vendor_id, pid, 'price', old_price=old_price, new_price=new_price))

        for attempt in range(3):
            try:
                # Insert logs into product_events table
                insert_logs_into_db(conn=supabase_client, product_events_logs=product_events_logs_to_insert)

                # Append vendor inventory to upload later
                vendor_inventories.update({str(vendor_id): new_inventory})
            except Exception as e:
                logging.error(f'Unexcepted error for vendor {vendor_id}: {e}. Reattempting upload.', exc_info=True)
                time.sleep(2 ** attempt)
        else:
            print(f'Failed to insert logs or update inventory for vendor {vendor_id}')

    for attempt in range(3):
        try:
            result = upload_vendors_inventories(supabase_client, vendor_inventories)
        except Exception as e:
            logging.error(f'Unexpected error: {e}. Reattempting upload', exc_info=True)
            time.sleep(2 ** attempt)
    else:
        logging.error(f'Failed to update vendor inventories.')

    # TODO: Function that checks whether any pricing errors were made. Implement with notifications.