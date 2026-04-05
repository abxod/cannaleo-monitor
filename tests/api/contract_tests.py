import os
import logging

import pytest
import requests
import json
from jsonschema import validate, ValidationError

from inventory.constants import CONST_BASE_API_PRODUCT_REQUEST_URL, CONST_VENDORS_INFORMATION_URL, CONST_PAGE_SIZE_LIMIT

# All the attributes in the original schema for Product are being retained for the sake of completeness.
# The following attributes are directly used in the program: 'id' (as a key in inventory dicts), 'url' (to generate product links), 'thc' and 'cbd' (for get_best_thc_price_ratio), 'dominance' (for get_best_thc_price_ration), 'min_price' and 'max_price', and 'availibility' and 'price'

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), 'schemas')


EMAIL_ADDRESS = os.environ['EMAIL_ADDRESS']
PASSWORD = os.environ['PASSWORD']

def _load_schema(
    path: str, ) -> dict:
    with open(path, 'r') as f:
        return json.load(f)


def assert_valid_schema(
    data,
    schema, ):
    """ Validate JSON data against a JSON schema. Raises on mismatch."""
    try:
        validate(instance=data, schema=schema)
    except ValidationError as e:
        pytest.fail(f'Schema validation failed: {e.message}')


class TestProductEndPointContract:
    PAGE = 1
    VENDOR_ID = 23
    PAYLOAD = {
        'pagination[page]': PAGE,
        'pagination[pageSize]': CONST_PAGE_SIZE_LIMIT,
        'vend': VENDOR_ID,
        'avail': 0
    }

    def test_product_endpoint_contract(
        self, ):
        schema = _load_schema(os.path.join(SCHEMA_DIR, 'products.json'))

        session = requests.Session()
        csrf_url = f'https://cannabisdarmstadt.de/api/auth/csrf'
        login_url = f'https://cannabisdarmstadt.de/api/auth/callback/credentials'
        product_url = f'https://cannabisdarmstadt.de/api/products'

        csrf_response = session.get(csrf_url)
        csrf_token = csrf_response.json()['csrfToken']
        login_response = session.post(
            login_url, data={
                'email': EMAIL_ADDRESS,
                'password': PASSWORD,
                'csrfToken': csrf_token
            }
            )

        response = session.get(product_url, params=self.PAYLOAD)

        assert response.status_code == 200
        assert response.headers['Content-Type'].startswith('application/json')
        data = response.json()
        assert_valid_schema(data, schema)


class TestVendorEndPointContract:
    def test_vendor_endpoint_contract(
        self, ):
        schema = _load_schema(os.path.join(SCHEMA_DIR, 'vendors.json'))

        response = requests.get(CONST_VENDORS_INFORMATION_URL)

        assert response.status_code == 200
        assert response.headers['Content-Type'].startswith('application/json')
        data = response.json()
        assert_valid_schema(data, schema)
