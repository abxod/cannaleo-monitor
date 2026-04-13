from datetime import datetime, timezone
from inventory.constants import (
    CONST_DB_PRODUCT_EVENT_TYPES,
    CONST_DB_VENDOR_EVENT_TYPES,
)
from models import ProductOffer

# TODO: The data types are not specific enough. Database tables use int2 for vendor_id and pid.


# TODO: These two functions seems identical, differing only in the event type passed
def log_product_change(
    vendor_id: int,
    pid: int,
    event_type: str,
    fetched_at,
    old_price: float = None,
    new_price: float = None,
    old_avail: str = None,
    new_avail=None,
):
    if event_type not in CONST_DB_PRODUCT_EVENT_TYPES:
        raise ValueError(f"Event type '{event_type}' is not defined. Skipping")

    return {
        "fetched_at": fetched_at,
        "vendor_id": vendor_id,
        "pid": pid,
        "event_type": event_type,
        "old_price": old_price,
        "new_price": new_price,
        "old_availability": old_avail,
        "new_availability": new_avail,
    }


def log_vendor_change(
    vendor_id: int,
    event_type: str,
    fetched_at,
    shipping_option: str = None,
    old_price: float = None,
    new_price: float = None,
    old_location: str = None,
    new_location: str = None,
):
    if event_type not in CONST_DB_VENDOR_EVENT_TYPES:
        raise ValueError(f"Event type '{event_type}' is not defined. Skipping")

    return {
        "fetched_at": fetched_at,
        "vendor_id": vendor_id,
        "event_type": event_type,
        "shipping_option": shipping_option,
        "old_price": old_price,
        "new_price": new_price,
        "old_location": old_location,
        "new_location": new_location,
    }


def log_product(vendor_id: int, pid: int, offer: ProductOffer, fetched_at):
    return {
        "fetched_at": fetched_at,
        "vendor_id": vendor_id,
        "pid": pid,
        "price": offer["price"],
        "availability": offer["availability"],
    }
