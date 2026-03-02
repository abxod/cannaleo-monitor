import logging
from dataclasses import dataclass
from typing import TypedDict, Optional, Any

from common.retry import with_retry
from inventory.supabase_io import load_json_from_bucket
from inventory.constants import CONST_SUPABASE_INVENTORIES_BUCKET, CONST_SUPABASE_VENDOR_ID_TO_OFFERS_FP


# TODO: Extract these into multiple files?
class ProductOffer(
    TypedDict
):
    price: float
    availability: str


class ShippingOptions(
    TypedDict
):
    shipping_cost_standard: Optional[float]
    express_cost_standard: Optional[float]
    local_coure_cost_standard: Optional[float]


class Address(
    TypedDict
):
    street: str
    postalcode: str
    city: str


class Coordinate(
    TypedDict
):
    latitude: float
    longitude: float


# TODO: Use this to diff vendors directly by overriding the == operator
@dataclass
class VendorInfo:
    id: str
    cannabis_pharmacy_name: str
    official_name: str
    domain: str
    email: str
    phone_number: str
    address: Address  # TODO: Implement this by editing from_scraping and from_supabase probably
    coordinates: Coordinate
    shipping_options: ShippingOptions

    @classmethod
    def from_json(
        cls,
        json_data: dict, ):
        return cls(
            id=json_data['id'],
            cannabis_pharmacy_name=json_data['cannabis_pharmacy_name'],
            official_name=json_data['official_name'],
            domain=json_data['domain'],
            email=json_data['email'],
            phone_number=json_data['phone_number'],
            address=Address(
                street=json_data['street'], postalcode=json_data['plz'], city=json_data['city'], ),
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


# TODO: Since this has to be
@dataclass
class Vendor:
    vendor_id: str
    info: VendorInfo
    inventory: dict[str, ProductOffer]

    # TODO: Should this be a class method?
    # TODO: Should this be a helper method somewhere other than in the class itself?
    @staticmethod
    def from_json(
        vendor_id: str,
        vendor_info: dict[str, dict],
        pid_to_price_availability: dict[str, dict], ):
        inventory = {}
        for pid, price_availability_dict in pid_to_price_availability.items():
            inventory[pid] = ProductOffer(
                price=price_availability_dict['price'], availability=price_availability_dict['availability']
            )

        return Vendor(
            vendor_id=vendor_id, info=VendorInfo.from_json(vendor_info), inventory=inventory
        )

    # TODO: Can this be a @staticmethod that just returns itself? Why do we need the Vendor object in the caller?
    # TODO: This method should set the look-ups of its object and return itself
    # TODO: Moving this workflow to main may be the best move. You would have access to new_pid_to_info
    # @classmethod
    # def from_scraping(
    #     cls,
    #     vendor_id: str,
    #     vendor_info: dict, ):
    #     from scraping import get_vendor_inventory, filter_vendor_inventory
    #
    #     try:
    #         pid_to_prod_info = get_vendor_inventory(vendor_id, vendor_info['domain'], with_price=True)
    #     except Exception as e:
    #         logging.error(f"Failed to scrape {vendor_info['domain']}: {e}")
    #         raise
    #
    #     filtered_inventory = filter_vendor_inventory(
    #         vendor_id=vendor_id, pid_to_prod_info=pid_to_prod_info, vendor_info=vendor_info
    #     )
    #
    #     logging.info(f'Inventory of vendor with vendor ID {vendor_id} successfully fetched from API')
    #
    #     return cls(
    #         vendor_id=vendor_id, info=VendorInfo.from_json(vendor_info), inventory=filtered_inventory
    #     )

    def get_inventory_as_dict(
        self, ) -> dict[str, dict[str, Any]]:
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
        old_vendor_id_to_info: dict, ):
        # TODO: Is this path necessary? We already fetch new vendor info from main.
        try:
            vendor_id_to_offers = with_retry(
                lambda: load_vendor_inventories(
                    client
                ), label='load_vendor_inventories(client)'
            )
            logging.info('Old vendor inventories successfully fetched from Supabase')
        except Exception:
            raise

        vendors: dict[str, Vendor] = {}
        for vendor_id, offers in vendor_id_to_offers.items():
            # double check this
            if vendor_id not in old_vendor_id_to_info:
                logging.warning(f'Vendor ID {vendor_id} found in inventories but not in vendor info. Skipping.') # This is the case when the script fails to fetch some vendor's inventory
                continue

            info = VendorInfo.from_json(
                old_vendor_id_to_info[vendor_id]
            )

            inventory: dict[str, ProductOffer] = {}
            for pid, raw_offer in offers.items():
                inventory[pid] = ProductOffer(
                    price=raw_offer['price'], availability=raw_offer['availability']
                )

            vendors[vendor_id] = Vendor(
                vendor_id=vendor_id, info=info, inventory=inventory, )
            logging.info(f'Vendor with vendor ID {vendors[vendor_id].vendor_id} instantiated.')

        return cls(
            vendors=vendors
        )

    # TODO: What do we think about this method's return type?  # @classmethod  # def from_scraping(  #     cls,  #     vendor_id_to_vendor_info: dict, ):  #     vendors = {}  #     pid_to_info: dict[str, Any] = {}  #  #     for vendor_id, vendor_info in sorted(vendor_id_to_vendor_info.items()):  #         time.sleep(2)  #  #         try:  #             pid_to_prod_info = get_vendor_inventory(vendor_id, vendor_info['domain'], with_price=True)  #         except Exception as e:  #             logging.error(f"Failed to scrape {vendor_id_to_vendor_info[vendor_id]['domain']}: {e}")  #             continue  #  #         vendor, vendor_pid_to_prod_info = filter_vendor_inventory(vendor_id, pid_to_prod_info, vendor_info, with_prod_info=True)  #         # vendor, vendor_prod_info = filter_vendor_inventory(  #         #     vendor_id, vendor_info, with_prod_info=True  #         # )  #  #         vendors[vendor_id] = vendor  #         pid_to_info.update(vendor_pid_to_prod_info)  #         logging.info(f'Inventory of vendor with vendor ID {vendor_id} successfully fetched from API')  #  #     return cls(vendors=vendors), pid_to_info
