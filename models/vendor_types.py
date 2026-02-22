from dataclasses import dataclass
from typing import TypedDict, Optional, Any
import logging
from common.geo import Coordinate


# TODO: Rename this source file
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


"""
This is not used for diffing vendors.
"""


# TODO: Make it.
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
