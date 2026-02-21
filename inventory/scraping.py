import os
import time
from typing import Any
import logging
import json
import requests

from constants import CONST_BASE_API_PRODUCT_REQUEST_URL, CONST_ALL_ATTRIBUTES, CONST_NEW_AVAILABILITY_OPTIONS, \
    CONST_AVAILABILITY_DB_MAP, CONST_VENDORS_INFORMATION_URL, CONST_PAGE_SIZE_LIMIT, CONST_FLOWZZ_PRODUCT_URL, \
    CONST_EXCLUDED_VENDOR_IDS
from vendor_types import ProductOffer
from common.retry import with_retry


EMAIL_ADDRESS = os.environ['EMAIL_ADDRESS']
PASSWORD = os.environ['PASSWORD']

def get_vendor_inventory(
    vendor_id: str,
    vendor_domain: str,
    availability: set[str] = None,
    with_price: bool = True, ) -> dict[str, dict[str | Any, Any]] | None:
    if availability is None:
        availability = CONST_NEW_AVAILABILITY_OPTIONS

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

        try:
            csrf_token = with_retry(
                lambda: session.get(
                    csrf_url
                ).json()['csrfToken']
                )
        except Exception:
            logging.error(f'Failed to get CSRF token for {vendor_id}.')
            raise

        session.post(
            login_url, data={
                'email': EMAIL_ADDRESS,
                'password': PASSWORD,
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
            1.5
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
        except Exception:
            raise

        if response.status_code != 200:
            raise Exception(
                f'Request failed  with {response.status_code}'
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

    logging.info(f'Fetched inventory from vendor ID {vendor_id}')
    return pid_to_prod_info


# TODO: I think this needs retry logic if we're decreasing the waiting time
# TODO: The condition-dependent return type is ugly.
# TODO: This function needs a better name
# TODO: Does this function belong here?
# TODO: This function should not return a Vendor object. It should return an inventory with specific look-ups filtered out
def filter_vendor_inventory(
    vendor_id: str,
    pid_to_prod_info: dict,
    vendor_info: dict,
    attributes: set[str] = None,
    availability: set[str] = None, ) -> dict[str, Any]:
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

    return filtered_inventory


def extract_price_availability(
    pid_to_prod_info: dict, ) -> dict[str, ProductOffer]:
    filtered_inventory = {}
    for pid, prod_info in pid_to_prod_info.items():
        product_offer: ProductOffer = {
            'price': prod_info['price'],
            'availability': CONST_AVAILABILITY_DB_MAP[prod_info['availibility']]
        }
        filtered_inventory[str(pid)] = product_offer

    return filtered_inventory


# TODO: Do you wanna define another class?
# TODO: This returns every attribute for each vendor. I think we have to change the structure to match that of the existing. No? Supabase also stores every attribute. It comes down to the diffing functions.
def get_vendors_information() -> dict:
    response = requests.get(
        CONST_VENDORS_INFORMATION_URL
    )

    raw_vendors_information = response.json()
    vendor_id_to_vendor_info = {str(vendor['vendor_id']): {k: v for k, v in vendor.items() if k != 'vendor_id'} for
                                vendor in raw_vendors_information['data']['pharmacies'] if
                                vendor['vendor_id'] not in CONST_EXCLUDED_VENDOR_IDS}
    return vendor_id_to_vendor_info


def scrape_vendor_inventory_and_products(
    vendor_id: str,
    vendor_info: dict, ) -> tuple[dict, dict]:
    try:
        pid_to_prod_info = get_vendor_inventory(vendor_id, vendor_info['domain'], with_price=True)
    except Exception as e:
        raise
    filtered_inventory = extract_price_availability(pid_to_prod_info)
    return filtered_inventory, pid_to_prod_info


def fetch_comments_from_strains():
    with open('../scraped_data/inventories/all_products.json', 'r') as f:
        pid_to_prod_info = json.load(f)

    with open('../scraped_data/all_reviews_test_2.json', 'r') as f:
        products_with_fetched_reviews = json.load(f)

    with open('../scripts/temp.txt', 'r') as f:
        malformed_pids = json.loads(f.read())

    pid_to_reviews = products_with_fetched_reviews.copy()

    for pid, prod_info in pid_to_prod_info.items():
        if pid != '2':
            continue

        prod_reviews = []
        start = 0
        while True:
            url_tail = f'{pid}?t=1&id={pid}&start={start}'
            full_url = CONST_FLOWZZ_PRODUCT_URL + url_tail

            try:
                response = with_retry(lambda: requests.get(full_url))
            except Exception:
                print(f'Failed to fetch comments of strain {pid} at {full_url}')
                break

            if response.status_code != 200:
                print(f'Request failed against {full_url} with {response.status_code}.')
                break

            reviews_page = response.json()['message']['data']['ratings']

            if len(reviews_page) == 0:
                break

            prod_reviews.extend(reviews_page)

            if len(reviews_page) < 10:
                break

            start += 10
            time.sleep(2)

        pid_to_reviews[pid] = prod_reviews
        if len(prod_reviews) != 0:
            print(f'Fetched reviews for {pid}.')

        time.sleep(2)

    with open('../scraped_data/all_reviews_test_2.json', 'w') as f:
        json.dump(pid_to_reviews, f, indent=2)

    print('Successfully fetched and stored all reviews.')