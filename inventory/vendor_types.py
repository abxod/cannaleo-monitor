from dataclasses import dataclass
from typing import TypedDict, Optional, Any
from common.geo import Coordinate

# TODO: Rename this source file
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
    cannabis_pharmacy_name: str
    official_name: str
    domain: str
    # address: Address # TODO: Implement this by editing from_scraping and from_supabase probably
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