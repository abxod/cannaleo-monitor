import time
import logging
from typing import Any

from inventory.models import Vendor
from scraping import scrape_filtered_vendor_inventory
from diffing import build_inventory_change_logs

def process_vendor(
    old_vendor: Vendor,
    new_vendor: Vendor
) -> list | None:
    vendor_id = old_vendor.vendor_id

    new_inventory = new_vendor.inventory
    old_inventory = old_vendor.inventory

    if new_inventory == old_inventory:
        logging.info(f'No inventory changes observed for {vendor_id}.')
        return None

    logs = build_inventory_change_logs(
        int(vendor_id),
        new_inventory,
        old_inventory,
    )

    return logs

def merge_all_products(new_inventory):
    pass