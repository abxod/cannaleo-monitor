import logging
from inventory.events import log_product_change, log_vendor_change, log_product
from models import ProductOffer, VendorDirectory
from inventory.constants import (
    CONST_SHIPPING_OPTIONS_KEYS,
    CONST_PRICE_LOWER_BOUND,
    CONST_PRICE_UPPER_BOUND,
)


# TODO: These functions can still be refactored (past ADDED/REMOVED)
def build_inventory_change_logs(
    vendor_id: int,
    old_inventory: dict[str, ProductOffer],
    new_inventory: dict[str, ProductOffer],
    fetched_at,
) -> list:
    logs = []

    new_pids = set(new_inventory.keys())
    old_pids = set(old_inventory.keys())

    # Added
    added = new_pids - old_pids
    added = [int(x) for x in added]
    for pid in added:
        log = log_product_change(vendor_id, pid, "ADDED", fetched_at)
        logs.append(log)

    # Removed
    removed = old_pids - new_pids
    removed = [int(x) for x in removed]
    for pid in removed:
        log = log_product_change(vendor_id, pid, "REMOVED", fetched_at)
        logs.append(log)

    intersection = new_pids & old_pids
    for pid in intersection:
        old = old_inventory[pid]
        new = new_inventory[pid]

        if old["availability"] != new["availability"]:
            log = log_product_change(
                vendor_id,
                int(pid),
                "AVAILABILITY",
                fetched_at,
                old_avail=old["availability"],
                new_avail=new["availability"],
            )
            logs.append(log)

        if old["price"] != new["price"]:
            log = log_product_change(
                vendor_id,
                int(pid),
                "PRICE",
                fetched_at,
                old_price=old["price"],
                new_price=new["price"],
            )
            logs.append(log)

    return logs


def build_inventory_logs(
    new_vendor_directory: VendorDirectory,
    fetched_at,
):
    inventory_logs = []
    vendors = new_vendor_directory.vendors
    for vendor_id, vendor in vendors.items():
        logging.debug(f"Building snapshot logs for vendor ID {vendor_id}")
        inventory = vendor.inventory
        for pid, offer in inventory.items():
            logging.debug(f"Building log for vendor ID {vendor_id} PID {pid}")
            product_log = log_product(
                int(vendor_id), int(pid), offer, fetched_at
            )  # TODO: Type conversion where?
            inventory_logs.append(product_log)

    return inventory_logs


def build_vendor_change_logs(
    old_vendors: dict,
    new_vendors: dict,
    fetched_at,
) -> list:
    logs = []

    # Added vendors
    added_vendor_ids = new_vendors.keys() - old_vendors.keys()
    for vendor_id in added_vendor_ids:
        log = log_vendor_change(vendor_id, "VENDOR_ADDED", fetched_at)
        logs.append(log)

    # Removed vendors
    removed_vendor_ids = old_vendors.keys() - new_vendors.keys()
    for vendor_id in removed_vendor_ids:
        log = log_vendor_change(vendor_id, "VENDOR_REMOVED", fetched_at)
        logs.append(log)

    for vendor_id in old_vendors.keys() & new_vendors.keys():
        old = old_vendors.get(vendor_id)
        new = new_vendors.get(vendor_id)

        old_filtered = {
            k: v for k, v in (old or {}).items() if k not in ("latitude", "longitude")
        }
        new_filtered = {
            k: v for k, v in (new or {}).items() if k not in ("latitude", "longitude")
        }

        if old_filtered == new_filtered:
            continue

        if old is None or new is None:
            continue

        # Shipping addition/removal
        # TODO: These only contain bools
        old_shipping_options = {
            "STANDARD": old.get("shipping_cost_standard"),
            "EXPRESS": old.get("express_cost_standard"),
            "LOCAL": old.get("local_coure_cost_standard"),
        }

        new_shipping_options = {
            "STANDARD": new.get("shipping_cost_standard"),
            "EXPRESS": new.get("express_cost_standard"),
            "LOCAL": new.get("local_coure_cost_standard"),
        }

        added_shipping_options = {
            opt
            for opt in CONST_SHIPPING_OPTIONS_KEYS
            if old_shipping_options.get(opt) is None
            and new_shipping_options.get(opt) is not None
        }
        removed_shipping_options = {
            opt
            for opt in CONST_SHIPPING_OPTIONS_KEYS
            if old_shipping_options.get(opt) is not None
            and new_shipping_options.get(opt) is None
        }

        if len(added_shipping_options) != 0:
            for shipping_option in added_shipping_options:
                log = log_vendor_change(
                    vendor_id, "SHIPPING_OPTION_ADDED", fetched_at, shipping_option
                )
                logs.append(log)

        if len(removed_shipping_options) != 0:
            for shipping_option in removed_shipping_options:
                log = log_vendor_change(
                    vendor_id, "SHIPPING_OPTION_REMOVED", fetched_at, shipping_option
                )
                logs.append(log)

        # Shipping price changes
        for shipping_option in CONST_SHIPPING_OPTIONS_KEYS:
            old_price = old_shipping_options[shipping_option]
            new_price = new_shipping_options[shipping_option]

            # Do not consider added or removed shipping options
            if old_price is None or new_price is None:
                continue

            # No pricing changes
            if old_price == new_price:
                continue

            log = log_vendor_change(
                vendor_id,
                "SHIPPING_PRICE_CHANGED",
                fetched_at,
                shipping_option.upper(),
                old_price=old_shipping_options[shipping_option],
                new_price=new_shipping_options[shipping_option],
            )
            logs.append(log)

        # Location change
        if old["street"] != new["street"]:
            event_type = "LOCATION_CHANGED"
            old_location = old["street"] + ", " + old["plz"] + " " + old["city"]
            new_location = new["street"] + ", " + new["plz"] + " " + new["city"]
            try:
                log = log_vendor_change(
                    vendor_id,
                    event_type,
                    fetched_at,
                    old_location=old_location,
                    new_location=new_location,
                )
            except ValueError:
                logging.error(f"Event type {event_type} is not defined. Skipping")
                continue
            logs.append(log)

    return logs


# TODO: This is prone to outliers
def build_new_daily_product_averages(
    pid_to_vendor_offers: dict[str, list[dict[str, str | float]]],
):
    new_averages = {}
    for pid, vendor_offers in pid_to_vendor_offers.items():
        valid_prices = [
            offer["price"]
            for offer in vendor_offers
            if CONST_PRICE_LOWER_BOUND <= offer["price"] <= CONST_PRICE_UPPER_BOUND
        ]

        if not valid_prices:
            continue

        new_averages[pid] = {
            "avg_price": sum(valid_prices) / len(valid_prices),
            "sample_count": len(valid_prices),
        }
    return new_averages


def build_daily_product_averages_logs(
    old_daily_product_averages: dict[str, dict[str, int | float]],
    new_daily_product_averages: dict[str, dict[str, int | float]],
    date: str,
) -> list[dict]:
    rows_to_upsert = []
    for pid, new in new_daily_product_averages.items():
        if pid in old_daily_product_averages:
            old = old_daily_product_averages[pid]
            total_count = old["sample_count"] + new["sample_count"]
            weighted_avg = (
                (old["avg_price"] * old["sample_count"])
                + (new["avg_price"] * new["sample_count"])
            ) / total_count
            rows_to_upsert.append(
                {
                    "date": date,
                    "pid": int(pid),
                    "avg_price": weighted_avg,
                    "sample_count": total_count,
                }
            )
        else:
            rows_to_upsert.append(
                {
                    "date": date,
                    "pid": int(pid),
                    "avg_price": new["avg_price"],
                    "sample_count": new["sample_count"],
                }
            )

    return rows_to_upsert
