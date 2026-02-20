from datetime import datetime, timezone
from inventory.constants import CONST_PRODUCT_EVENT_TYPES, CONST_VENDOR_EVENT_TYPES

def log_product(vendor_id, pid, event_type, old_price=None, new_price=None, old_avail=None, new_avail=None):
    if event_type not in CONST_PRODUCT_EVENT_TYPES:
        raise ValueError(f'Event type \'{event_type}\' is not defined. Skipping.')

    return {
        'timestamp': datetime.now(timezone.utc),
        'vendor_id': vendor_id,
        'pid': pid,
        'event_type': event_type,
        'old_price': old_price,
        'new_price': new_price,
        'old_availability': old_avail,
        'new_availability': new_avail,
    }

def log_vendor(vendor_id, event_type, shipping_option=None, old_price=None, new_price=None, old_location=None, new_location=None):
    if event_type not in CONST_VENDOR_EVENT_TYPES:
        raise ValueError(f'Event type \'{event_type}\' is not defined. Skipping.')

    return {
        'created_at': datetime.now(timezone.utc).isoformat(),
        'vendor_id': vendor_id,
        'event_type': event_type,
        'shipping_option': shipping_option,
        'old_price': old_price,
        'new_price': new_price,
        'old_location': old_location,
        'new_location': new_location,
    }