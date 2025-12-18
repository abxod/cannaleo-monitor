import time
from typing import Any
import logging
import json
import requests
from models import Vendor, ProductOffer, VendorInfo
from constants import *


def scrape_filtered_vendor_inventory(
    vendor_id: str,
    vendor_domain: str,
    attributes: set[str] = None,
    availability: set[str] = None, ) -> dict[str, dict[str | Any, Any]] | None:
    if attributes is None:
        attributes = CONST_ALL_ATTRIBUTES
    if availability is None:
        availability = CONST_AVAILABILITY_OPTIONS

    if vendor_id not in CONST_ALL_VENDOR_IDS:
        raise ValueError(
            f'Vendor with vendor ID {vendor_id} does not exist.'
        )

    invalid_attributes = attributes - CONST_ALL_ATTRIBUTES
    valid_attributes = attributes - invalid_attributes
    if invalid_attributes:
        print(
            f'Non-existent attributes: {list(dict.fromkeys(invalid_attributes))}\nProceeding with {valid_attributes}'
        )

    if 'price' in valid_attributes:
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

    filtered_inventory = {}
    for pid, prod_info in pid_to_prod_info.items():
        # TODO: Update this
        if prod_info.get(
            'availibility'
        ) not in availability:
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
    return filtered_inventory


# TODO: I think this needs retry logic if we're decreasing the waiting time
# TODO: THIS USES NOMINATIM. UNDO THAT.
def scrape_vendor_inventory_price_availability(
    vendor_id: str,
    vendor_info: dict,
    availability: set[str] = None, ) -> Vendor:
    try:
        filtered_dict = scrape_filtered_vendor_inventory(
            vendor_id, vendor_info['domain'], attributes={'price', 'availibility'}, availability=availability
        )
    except Exception as e:
        raise

    inventory = {}
    for pid, info in filtered_dict.items():
        inventory[pid] = ProductOffer(
            price=info['price'], availability=info['availability']
        )

    return Vendor(
        vendor_id=vendor_id, info=VendorInfo.from_json(vendor_info), inventory=inventory
    )


# TODO: Do you wanna define another class?
# TODO: This returns every attribute for each vendor. I think we have to change the structure to match that of the existing. No? Supabase also stores every attribute. It comes down to the diffing functions.
def get_vendors_information() -> dict:
    response = requests.get(
        CONST_VENDORS_INFORMATION_URL
    )

    raw_vendors_information = response.json()
    vendor_id_to_vendor_info = {vendor['vendor_id']: {k: v for k, v in vendor.items() if k != 'vendor_id'} for vendor in
                                raw_vendors_information['data']['pharmacies']}

    return vendor_id_to_vendor_info
