import logging
from events import log_product, log_vendor
from models import ProductOffer
from constants import CONST_SHIPPING_OPTIONS_KEYS


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
    for pid in new_pids - old_pids:
        event_type = 'ADDED'
        try:
            log = log_product(
                vendor_id, pid, event_type
            )
        except ValueError:
            logging.error(
                f'Event type {event_type} is not defined. Skipping.'
            )
            continue
        logs.append(
            log
        )

    # Removed
    for pid in old_pids - new_pids:
        event_type = 'REMOVED'
        try:
            log = log_product(
                vendor_id, pid, event_type
            )
        except ValueError:
            logging.error(
                f'Event type {event_type} is not defined. Skipping.'
            )
            continue
        logs.append(
            log
        )

    for pid in new_pids & old_pids:
        old = old_inventory[pid]
        new = new_inventory[pid]

        if old['availability'] != new['availability']:
            event_type = 'AVAILABILITY'
            try:
                log = log_product(
                    vendor_id, pid, event_type, old_avail=old['availability'], new_avail=new['availability']
                )
            except ValueError:
                logging.error(
                    f'Event type {event_type} is not defined. Skipping.'
                )
                continue
            logs.append(
                log
            )

        if old['price'] != new['price']:
            event_type = 'PRICE'
            try:
                log = log_product(
                    vendor_id, pid, event_type, old_price=old['price'], new_price=new['price']
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


def build_vendor_change_logs(
    old_vendors: dict,
    new_vendors: dict, ) -> list:
    logs = []

    all_vendor_ids = old_vendors.keys() | new_vendors.keys()

    for vendor_id in all_vendor_ids:
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

        # Vendor added
        if old is None and new is not None:
            event_type = 'VENDOR_ADDED'
            try:
                log = log_vendor(
                    vendor_id, 'VENDOR_ADDED'
                )
            except ValueError:
                logging.error(
                    f'Event type {event_type} is not defined. Skipping.'
                )
                continue
            logs.append(
                log
            )

        # Vendor removed
        if old is not None and new is None:
            event_type = 'VENDOR_REMOVED'
            try:
                log = log_vendor(
                    vendor_id, 'VENDOR_REMOVED'
                )
            except ValueError:
                logging.error(
                    f'Event type {event_type} is not defined. Skipping.'
                )
                continue
            logs.append(
                log
            )

        if old is None or new is None:
            continue

        # Shipping addition/removal
        # TODO: These only contain bools
        old_shipping_options = {
            'standard': old.get(
                'shipping_cost_standard'
            ),
            'express': old.get(
                'express_cost_standard'
            ),
            'local': old.get(
                'local_coure_cost_standard'
            ),
        }

        new_shipping_options = {
            'standard': new.get(
                'shipping_cost_standard'
            ),
            'express': new.get(
                'express_cost_standard'
            ),
            'local': new.get(
                'local_coure_cost_standard'
            ),
        }

        added = {opt for opt in CONST_SHIPPING_OPTIONS_KEYS if old_shipping_options.get(
            opt
        ) is None and new_shipping_options.get(
            opt
        ) is not None}
        removed = {opt for opt in CONST_SHIPPING_OPTIONS_KEYS if old_shipping_options.get(
            opt
        ) is not None and new_shipping_options.get(
            opt
        ) is None}

        if len(
            added
        ) != 0:
            for shipping_option in added:
                event_type = 'SHIPPING_OPTION_ADDED'
                try:
                    log = log_vendor(
                        vendor_id, event_type, shipping_option
                    )
                except ValueError:
                    logging.error(
                        f'Event type {event_type} is not defined. Skipping.'
                    )
                    continue
                logs.append(
                    log
                )

        if len(
            removed
        ) != 0:
            for shipping_option in removed:
                event_type = 'SHIPPING_OPTION_REMOVED'
                try:
                    log = log_vendor(
                        vendor_id, event_type, shipping_option
                    )
                except ValueError:
                    logging.error(
                        f'Event type {event_type} is not defined. Skipping.'
                    )
                    continue
                logs.append(
                    log
                )

        # Shipping price changes
        for shipping_option in CONST_SHIPPING_OPTIONS_KEYS:
            if old_shipping_options[shipping_option] != new_shipping_options[shipping_option]:
                event_type = 'SHIPPING_PRICE_CHANGED'
                try:
                    log = log_vendor(
                        vendor_id, event_type, shipping_option.upper(), old_price=old_shipping_options[shipping_option], new_price=new_shipping_options[shipping_option]
                    )
                except ValueError:
                    logging.error(
                        f'Event type {event_type} is not defined. Skipping.'
                    )
                    continue
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
