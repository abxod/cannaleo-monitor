import logging
import os
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import supabase

from common.retry import with_retry
from inventory.constants import (
    CONST_SUPABASE_VENDOR_ID_TO_INFO_BUCKET,
    CONST_SUPABASE_VENDOR_ID_TO_INFO_FP,
)
from inventory.diffing import (
    build_daily_product_averages_logs,
    build_inventory_logs,
    build_new_daily_product_averages,
    build_vendor_change_logs,
)
from inventory.scraping import (
    get_vendors_information,
    scrape_vendor_inventory_and_products,
)
from inventory.service import (
    get_coordinates_of_affected_vendors,
    merge_all_products,
    process_vendors,
)
from inventory.supabase_io import (
    get_daily_product_averages,
    load_json_from_bucket,
    push_results_to_supabase,
)
from models import Vendor, VendorDirectory, VendorInfo

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
# TODO: pid_to_info should keep a look-up table that is UPDATED not OVERWRITTEN
# TODO: Use 'type' instead of the convoluted 'dict[str, Any]' syntax, or TypedDicts for fuck's sake

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

log_path = Path.cwd() / "execution_logs.log"

logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# TODO: Figure out logging
# TODO: The function is getting ugly. Refactor it again
# TODO: run() should reside in another module


def run(
    conn,
):
    fetched_at = datetime.now(timezone.utc).isoformat()
    today = date.today().isoformat()

    # Fetch old vendor information JSON from Supabase
    logging.info("Fetching vendor information from Supabase")
    try:
        old_vendor_id_to_info = with_retry(
            lambda: load_json_from_bucket(
                conn,
                CONST_SUPABASE_VENDOR_ID_TO_INFO_BUCKET,
                CONST_SUPABASE_VENDOR_ID_TO_INFO_FP,
            ),
            label=f"load_vendors_information(conn)",
        )
    except Exception as e:
        logging.error(f"Failed to fetch vendor information from Supabase: {e}")
        sys.exit(1)

    # Fetch new vendor information JSON from API
    logging.info("Fetching vendor information from API")
    try:
        new_vendor_id_to_info = with_retry(
            lambda: get_vendors_information(), label="get_vendors_information()"
        )
    except Exception as e:
        logging.error(f"Failed to get vendor information: {e}")
        sys.exit(1)

    # Diff-check inventories
    logging.info("Fetching old vendor inventories from Supabase")
    try:
        old_vendor_directory = VendorDirectory.from_supabase(
            conn, old_vendor_id_to_info
        )
    except Exception as e:
        logging.error(
            f"Old inventories could not be fetched from Supabase: {e}", exc_info=True
        )
        sys.exit(1)

    logging.info(f"Fetching daily product averages for {today} from Supabase")
    try:
        old_daily_product_averages_rows = with_retry(
            lambda: get_daily_product_averages(conn, today),
            label=f"get_daily_product_averages{today}",
        )
        old_daily_product_averages_by_pid = {
            str(row["pid"]): {
                "avg_price": row["avg_price"],
                "sample_count": row["sample_count"],
            }
            for row in old_daily_product_averages_rows
        }
    except Exception as e:
        logging.error(f"Failed to fetch daily product averages: {e}")
        sys.exit(1)

    logging.info("Starting inventory fetch via API")
    vendor_id_to_offers = {}
    all_pid_to_prod_info = {}
    new_vendor_directory = VendorDirectory()
    for vendor_id, vendor_info in new_vendor_id_to_info.items():
        # TODO: I think checking whether old_inventories.vendors.get(vendor_id) for nullability makes more sense and is more explicit here.
        try:
            filtered_inventory, new_pid_to_info = scrape_vendor_inventory_and_products(
                vendor_id, vendor_info
            )
            new_vendor = Vendor(
                vendor_id=vendor_id,
                info=VendorInfo.from_json(vendor_info),
                inventory=filtered_inventory,
            )
            new_vendor_directory.vendors[vendor_id] = new_vendor
        except Exception as e:
            logging.error(
                f"Skipping due to failed vendor fetch for vendor ID {vendor_id}: {e}"
            )
            continue

        # TODO: This shouldn't have to be done
        vendor_id_to_offers[vendor_id] = new_vendor.get_inventory_as_dict()

        # Update all_products
        # TODO: This could theoretically be placed outside the for-loop, but that would require to save this redundant information n times (n = num_vendors), no?
        all_pid_to_prod_info = merge_all_products(all_pid_to_prod_info, new_pid_to_info)

        time.sleep(2.0)

    if not new_vendor_directory.vendors:
        logging.error("Failed to fetch any inventory")
        sys.exit(1)

    # Generate logs for changes in vendors' shipping prices or locations
    logging.info("Building vendor change logs")
    vendor_logs = build_vendor_change_logs(
        old_vendor_id_to_info, new_vendor_id_to_info, fetched_at
    )
    logging.info("Building inventory changes logs")
    offer_changes_logs = process_vendors(
        old_vendor_directory, new_vendor_directory, fetched_at
    )
    logging.info("Building offer snapshot logs")
    offer_logs = build_inventory_logs(new_vendor_directory, fetched_at)

    pid_to_vendor_offers = {}
    for vendor_id, offers in vendor_id_to_offers.items():
        for pid, offer in offers.items():
            if pid not in pid_to_vendor_offers:
                pid_to_vendor_offers[pid] = []
            pid_to_vendor_offers[pid].append(
                {
                    "vendor_id": vendor_id,
                    "price": offer["price"],
                    "availability": offer["availability"],
                }
            )

    for pid, vendor_offers in pid_to_vendor_offers.items():
        try:
            pid_to_vendor_offers[pid].sort(key=lambda x: x["price"])
        except TypeError as e:
            logging.fatal(
                f"The following contains NULL pricing: {pid_to_vendor_offers[pid]}.\nYou have to check the prices in the DB next.: {e}"
            )
            continue

    updated_vendors_information = get_coordinates_of_affected_vendors(
        vendor_logs, old_vendor_id_to_info, new_vendor_id_to_info
    )

    new_daily_product_averages = build_new_daily_product_averages(pid_to_vendor_offers)
    daily_product_averages_logs = build_daily_product_averages_logs(
        old_daily_product_averages_by_pid, new_daily_product_averages, today
    )

    push_results_to_supabase(
        conn,
        offer_changes_logs=offer_changes_logs,
        offer_logs=offer_logs,
        daily_product_averages_logs=daily_product_averages_logs,
        vendor_logs=vendor_logs,
        vendor_id_to_offers=vendor_id_to_offers,
        pid_to_vendor_offers=pid_to_vendor_offers,
        all_pid_to_prod_info=all_pid_to_prod_info,
        updated_vendors_information=updated_vendors_information,
    )

    logging.info(f"Terminating script")


if __name__ == "__main__":
    logging.info("Starting script")
    logging.info("Creating Supabase connection")
    conn = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
    run(conn)
    logging.info("Terminating script")
