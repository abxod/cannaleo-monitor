import sys
from dataclasses import dataclass
import logging
from inventory.supabase_io import load_vendor_inventories, load_vendors_information
from common.retry import with_retry
from models.vendor_types import Vendor, ProductOffer, VendorInfo


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
        vendor_id_to_vendor_info: dict, ):
        # TODO: Is this path necessary? We already fetch new vendor info from main.
        try:
            vendor_id_to_inventory = with_retry(
                lambda: load_vendor_inventories(
                    client
                ), label='load_vendor_inventories(client)'
                )
            logging.info('Old vendor inventories successfully fetched from Supabase')
        except Exception:
            raise

        vendors: dict[str, Vendor] = {}
        for vendor_id, inventory_json in vendor_id_to_inventory.items():
            # double check this
            if vendor_id not in vendor_id_to_vendor_info:
                logging.warning(f'Vendor ID {vendor_id} found in inventories but not in vendor info. Skipping.')
                continue

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
            logging.info(f'Vendor with vendor ID {vendors[vendor_id].vendor_id} instantiated.')

        return cls(
            vendors=vendors
        )

    # TODO: What do we think about this method's return type?
    # @classmethod
    # def from_scraping(
    #     cls,
    #     vendor_id_to_vendor_info: dict, ):
    #     vendors = {}
    #     pid_to_info: dict[str, Any] = {}
    #
    #     for vendor_id, vendor_info in sorted(vendor_id_to_vendor_info.items()):
    #         time.sleep(2)
    #
    #         try:
    #             pid_to_prod_info = get_vendor_inventory(vendor_id, vendor_info['domain'], with_price=True)
    #         except Exception as e:
    #             logging.error(f"Failed to scrape {vendor_id_to_vendor_info[vendor_id]['domain']}: {e}")
    #             continue
    #
    #         vendor, vendor_pid_to_prod_info = filter_vendor_inventory(vendor_id, pid_to_prod_info, vendor_info, with_prod_info=True)
    #         # vendor, vendor_prod_info = filter_vendor_inventory(
    #         #     vendor_id, vendor_info, with_prod_info=True
    #         # )
    #
    #         vendors[vendor_id] = vendor
    #         pid_to_info.update(vendor_pid_to_prod_info)
    #         logging.info(f'Inventory of vendor with vendor ID {vendor_id} successfully fetched from API')
    #
    #     return cls(vendors=vendors), pid_to_info
