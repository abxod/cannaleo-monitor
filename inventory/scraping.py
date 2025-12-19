import time
from typing import Any
import logging
import json
import requests

from constants import *
from inventory.vendor_types import Vendor, VendorInfo, ProductOffer

def get_vendor_inventory(
    vendor_id: str,
    vendor_domain: str,
    availability: set[str] = None,
    with_price: bool = True, ) -> dict[str, dict[str | Any, Any]] | None:
    if availability is None:
        availability = CONST_AVAILABILITY_OPTIONS

    # TODO: This is not sustainable.
    # if vendor_id not in CONST_ALL_VENDOR_IDS:
    #     raise ValueError(
    #         f'Vendor with vendor ID {vendor_id} does not exist.'
    #     )

    if with_price:
        use_session = True
    else:
        use_session = False

    if use_session:
        session = requests.Session()
        vendor_domain = vendor_domain
        base_url = f'https://{vendor_domain}/api/products'
        csrf_url = f'https://{vendor_domain}/api/auth/csrf'
        login_url = f'https://{vendor_domain}/api/auth/callback/credentials'

        csrf_token = session.get(
            csrf_url
        ).json()['csrfToken']

        session.post(
            login_url, data={
                'email': CONST_EMAIL,
                'password': CONST_PASSWORD,
                'csrfToken': csrf_token
            }
        )

        request_fn = session.get
    else:
        base_url = CONST_BASE_API_PRODUCT_REQUEST_URL
        request_fn = requests.get

    page = 1
    pid_to_prod_info = {}
    while True:
        time.sleep(
            0.5
        )  # Don't disrupt service

        payload = {
            'pagination[page]': page,
            'pagination[pageSize]': CONST_PAGE_SIZE_LIMIT,
            'vend': vendor_id,  # TODO: Does this have to be an int?
            'avail': 0 if 'unavailable' in availability else 1
        }

        try:
            response = request_fn(
                base_url, params=payload
            )
        except Exception as e:
            raise

        if response.status_code != 200:
            raise Exception(
                f'Request failed with {response.status_code}'
            )

        json_obj = response.json()
        products_data_array = json_obj['message']['data']

        if products_data_array:
            pid_to_prod_info.update(
                {p['id']: p for p in products_data_array}
            )

        page_count = json_obj['message']['meta']['pagination']['pageCount']
        if page >= page_count:
            break

        page += 1

    return pid_to_prod_info


# TODO: I think this needs retry logic if we're decreasing the waiting time
# TODO: The condition-dependent return type is ugly.
# This function needs a better name
def filter_vendor_inventory(
    vendor_id: str,
    pid_to_prod_info: dict,
    vendor_info: dict,
    with_prod_info: bool,
    attributes: set[str] = None,
    availability: set[str] = None, ) -> tuple[Vendor, dict[str, dict[str | Any, Any]] | None] | Vendor:
    if attributes is None:
        attributes = CONST_ALL_ATTRIBUTES

    if availability is None:
        availability = CONST_NEW_AVAILABILITY_OPTIONS

    invalid_attributes = attributes - CONST_ALL_ATTRIBUTES
    valid_attributes = attributes - invalid_attributes
    if invalid_attributes:
        print(
            f'Non-existent attributes: {list(dict.fromkeys(invalid_attributes))}\nProceeding with {valid_attributes}'
        )

    filtered_inventory = {}
    for pid, prod_info in pid_to_prod_info.items():
        # TODO: Update this
        prod_availability = CONST_AVAILABILITY_DB_MAP[prod_info.get('availibility')]
        if prod_availability not in availability:
            continue

        prod_info_normalized = {}
        for k in valid_attributes:
            if k not in prod_info or k == 'id':
                continue

            if k == 'availibility':
                prod_info_normalized['availability'] = CONST_AVAILABILITY_DB_MAP[prod_info[k]]
            else:
                prod_info_normalized[k] = prod_info[k]

        filtered_inventory[pid] = prod_info_normalized

    inventory = {}
    for pid, info in filtered_inventory.items():
        inventory[pid] = ProductOffer(
            price=info['price'], availability=info['availability']
        )

    vendor = Vendor(
        vendor_id=vendor_id, info=VendorInfo.from_json(vendor_info), inventory=inventory
    )

    if with_prod_info:
        return vendor, pid_to_prod_info
    else:
        return vendor


# TODO: Do you wanna define another class?
# TODO: This returns every attribute for each vendor. I think we have to change the structure to match that of the existing. No? Supabase also stores every attribute. It comes down to the diffing functions.
def get_vendors_information() -> dict:
    response = requests.get(
        CONST_VENDORS_INFORMATION_URL
    )

    raw_vendors_information = response.json()
    vendor_id_to_vendor_info = {str(vendor['vendor_id']): {k: v for k, v in vendor.items() if k != 'vendor_id'} for vendor in
                                raw_vendors_information['data']['pharmacies']}

    return vendor_id_to_vendor_info
