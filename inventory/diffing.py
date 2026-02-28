import logging
from inventory.events import log_product, log_vendor
from models.models import ProductOffer
from models import ProductOffer, VendorDirectory
from inventory.constants import CONST_SHIPPING_OPTIONS_KEYS


# TODO: These functions can still be refactored (past ADDED/REMOVED)
def build_inventory_change_logs(
    vendor_id: int,
    new_inventory: dict[str, ProductOffer],
    old_inventory: dict[str, ProductOffer], ) -> list:
    logs = []

    new_pids = set(
        new_inventory.keys()
    )
    old_pids = set(
        old_inventory.keys()
    )

    # Added
    added = new_pids - old_pids
    added = [int(x) for x in added]
    for pid in added:
        log = log_product(
            vendor_id, pid, 'ADDED'
        )
        logs.append(
            log
        )

    # Removed
    removed = old_pids - new_pids
    removed = [int(x) for x in removed]
    for pid in removed:
        log = log_product(
            vendor_id, pid, 'REMOVED'
        )
        logs.append(
            log
        )

    intersection = new_pids & old_pids
    for pid in intersection:
        old = old_inventory[pid]
        new = new_inventory[pid]

        if old['availability'] != new['availability']:
            log = log_product(
                vendor_id,
                int(pid),
                'AVAILABILITY',
                old_avail=old['availability'].upper(),
                new_avail=new['availability'].upper()
            )
            logs.append(
                log
            )

        if old['price'] != new['price']:
            log = log_product(
                vendor_id, int(pid), 'PRICE', old_price=old['price'], new_price=new['price']
            )
            logs.append(
                log
            )

    return logs


def build_vendor_change_logs(
    old_vendors: dict,
    new_vendors: dict, ) -> list:
    logs = []

    # Added vendors
    added_vendor_ids = new_vendors.keys() - old_vendors.keys()
    for vendor_id in added_vendor_ids:
        log = log_vendor(vendor_id, 'VENDOR_ADDED')
        logs.append(log)

    # Removed vendors
    removed_vendor_ids = old_vendors.keys() - new_vendors.keys()
    for vendor_id in removed_vendor_ids:
        log = log_vendor(vendor_id, 'VENDOR_REMOVED')
        logs.append(log)

    for vendor_id in old_vendors.keys() & new_vendors.keys():
        old = old_vendors.get(
            vendor_id
        )
        new = new_vendors.get(
            vendor_id
        )

        old_filtered = {k: v for k, v in (old or {}).items() if k not in ('latitude', 'longitude')}
        new_filtered = {k: v for k, v in (new or {}).items() if k not in ('latitude', 'longitude')}

        if old_filtered == new_filtered:
            continue

        if old is None or new is None:
            continue

        # Shipping addition/removal
        # TODO: These only contain bools
        old_shipping_options = {
            'STANDARD': old.get(
                'shipping_cost_standard'
            ),
            'EXPRESS': old.get(
                'express_cost_standard'
            ),
            'LOCAL': old.get(
                'local_coure_cost_standard'
            ),
        }

        new_shipping_options = {
            'STANDARD': new.get(
                'shipping_cost_standard'
            ),
            'EXPRESS': new.get(
                'express_cost_standard'
            ),
            'LOCAL': new.get(
                'local_coure_cost_standard'
            ),
        }

        added_shipping_options = {opt for opt in CONST_SHIPPING_OPTIONS_KEYS if old_shipping_options.get(
            opt
        ) is None and new_shipping_options.get(
            opt
        ) is not None}
        removed_shipping_options = {opt for opt in CONST_SHIPPING_OPTIONS_KEYS if old_shipping_options.get(
            opt
        ) is not None and new_shipping_options.get(
            opt
        ) is None}

        if len(
            added_shipping_options
        ) != 0:
            for shipping_option in added_shipping_options:
                log = log_vendor(
                    vendor_id, 'SHIPPING_OPTION_ADDED', shipping_option
                )
                logs.append(
                    log
                )

        if len(
            removed_shipping_options
        ) != 0:
            for shipping_option in removed_shipping_options:
                log = log_vendor(
                    vendor_id, 'SHIPPING_OPTION_REMOVED', shipping_option
                )
                logs.append(
                    log
                )

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

            log = log_vendor(
                vendor_id,
                'SHIPPING_PRICE_CHANGED',
                shipping_option.upper(),
                old_price=old_shipping_options[shipping_option],
                new_price=new_shipping_options[shipping_option]
            )
            logs.append(
                log
            )

        # Location change
        if old['street'] != new['street']:
            event_type = 'LOCATION_CHANGED'
            old_location = old['street'] + ', ' + old['plz'] + ' ' + old['city']
            new_location = new['street'] + ', ' + new['plz'] + ' ' + new['city']
            try:
                log = log_vendor(
                    vendor_id, event_type, old_location=old_location, new_location=new_location
                )
            except ValueError:
                logging.error(
                    f'Event type {event_type} is not defined. Skipping.'
                )
                continue
            logs.append(
                log
            )

    return logs
