import sys
import time
from dataclasses import dataclass, field
from typing import TypedDict, Tuple, Optional, Any
import logging
from supabase_io import load_vendor_inventories, load_vendors_information
from common.retry import with_retry
from scraping import scrape_vendor_inventory_price_availability
from constants import CONST_AVAILABILITY_OPTIONS
import events
from common.geo import Coordinate


# TODO: Extract these into multiple files?
class ProductOffer(
    TypedDict
):
    price: float
    availability: int


class ShippingOptions(
    TypedDict
):
    shipping_cost_standard: Optional[float]
    express_cost_standard: Optional[float]
    local_coure_cost_standard: Optional[float]

"""
This is not used for diffing vendors.
"""
@dataclass
class VendorInfo:
    cannabis_pharmacy_name: str
    official_name: str
    domain: str
    coordinates: Coordinate
    shipping_options: ShippingOptions

    @classmethod
    def from_json(
        cls,
        json_data: dict, ):
        return cls(
            cannabis_pharmacy_name=json_data['cannabis_pharmacy_name'],
            official_name=json_data['official_name'],
            domain=json_data['domain'],
            coordinates=Coordinate(latitude=json_data.get('latitude', 0), longitude=json_data.get('longitude', 0)),
            shipping_options=ShippingOptions(
                shipping_cost_standard=json_data.get(
                    'shipping_cost_standard'
                ), express_cost_standard=json_data.get(
                    'express_cost_standard'
                ), local_coure_cost_standard=json_data.get(
                    'local_coure_cost_standard'
                )
            )
        )


@dataclass
class Vendor:
    vendor_id: str
    info: VendorInfo
    inventory: dict[str, ProductOffer]

    def get_inventory_as_dict(
        self
        ) -> dict[str, dict[str, Any]]:
        """Convert inventory ProductOffer objects to plain dictionaries."""
        return {pid: {
            'price': offer['price'],
            'availability': offer['availability']
        } for pid, offer in self.inventory.items()}


@dataclass
class VendorDirectory:
    vendors: dict[str, Vendor] = None

    def __post_init__(
        self, ):
        if self.vendors is None:
            self.vendors = {}

    @classmethod
    def from_supabase(
        cls,
        client,
        vendor_id_to_vendor_info: dict = None, ):
        if vendor_id_to_vendor_info is None:
            try:
                vendor_id_to_vendor_info = with_retry(
                    lambda: load_vendors_information(
                        client
                    )
                )
            except Exception as e:
                logging.error(
                    f'Failed to fetch vendors\' information: {e}'
                )
                sys.exit(
                    1
                )

        try:
            vendor_id_to_inventory = with_retry(
                lambda: load_vendor_inventories(
                    client
                )
            )
        except Exception as e:
            logging.error(
                f'Failed to fetch vendor inventories: {e}'
            )
            sys.exit(
                1
            )

        vendors: dict[str, Vendor] = {}
        for vendor_id, inventory_json in vendor_id_to_inventory.items():
            info = VendorInfo.from_json(
                vendor_id_to_vendor_info[vendor_id]
            )

            inventory: dict[str, ProductOffer] = {}
            for pid, raw_offer in inventory_json.items():
                inventory[pid] = ProductOffer(
                    price=raw_offer['price'], availability=raw_offer['availability']
                )

            vendors[vendor_id] = Vendor(
                vendor_id=vendor_id, info=info, inventory=inventory, )

        return cls(
            vendors=vendors
        )

    @classmethod
    def from_scraping(
        cls,
        vendor_id_to_vendor_info: dict, ):
        vendors = {}
        for vendor_id, vendor_info in vendor_id_to_vendor_info.items():
            time.sleep(2)

            try:
                vendor = scrape_vendor_inventory_price_availability(
                    vendor_id, vendor_info
                )

                vendors[vendor_id] = vendor
            except Exception as e:
                logging.error(f'Failed to scrape {vendor_id_to_vendor_info[vendor_id]['domain']: {e}}')
                continue
        return cls(
            vendors=vendors
        )
