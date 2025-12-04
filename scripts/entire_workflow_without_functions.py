import requests
import json
import os
import datetime

os.environ['NTFY_TOPIC'] = 'cqDge025U6rTAogEqvVR'
topic = os.environ['NTFY_TOPIC']

page = 1
CONST_PAGE_SIZE_LIMIT = 50
vendor_id = 329

base_api_request_url = 'https://www.cannaleo.de/api/products'

all_products_json = []
while True:
    # Add sort and availability parameters
    payload = {'pagination[page]': page, 'pagination[pageSize]': CONST_PAGE_SIZE_LIMIT, 'vend': vendor_id}
    response = requests.get(base_api_request_url, params=payload)
    response_url = response.url
    if response.status_code != 200:
        raise Exception(f'Request failed with {response.status_code}')

    json_obj = response.json()
    products_data = json_obj['message']['data']

    meta_information = json_obj['message']['meta']
    page_count = meta_information['pagination']['pageCount']
    if page > page_count:
        break

    if products_data:
        all_products_json.extend(json_obj.get('message', {}).get('data', []))

    page += 1

print("Number of products fetched:", len(all_products_json))

# Extract the ID and the name of each strain from the JSON object into a new JSON object
products_id_and_name = [{'id': int(p['id']), 'name': p['name']} for p in all_products_json]

new_product_ids_set = {int(product['id']) for product in all_products_json}
with open('../scraped_data/latest_inventory_id_name/darmstadt.json', 'r') as f:
    old_product_ids_names_json = json.load(f)
old_product_ids_set = {int(product_id_name['id']) for product_id_name in old_product_ids_names_json}

added = new_product_ids_set - old_product_ids_set
removed = old_product_ids_set - new_product_ids_set

new_product_ids_set.add(2163)
print('New product IDs:', new_product_ids_set)

# If set not empty
if added:
    if 2163 in new_product_ids_set:
        requests.post(f'https://ntfy.sh/{topic}', data='Drapalin Full Gas is back in stock 🌿'.encode(encoding='utf-8'))
    else:
        requests.post(f'https://ntfy.sh/{topic}', data='Not back in stock just yet 😔')
else:
    requests.post(f'https://ntfy.sh/{topic}', data='No inventory changes observed.')

# Save the extracted products and IDs (with timestamps)
with open('../scraped_data/latest_inventory_id_name/darmstadt.json', 'w') as f:
    json.dump(products_id_and_name, f, indent=2)
    print(f'Saved product IDs and names to darmstadt.json')

# # store_inventory
# pharmacy = 'darmstadt'
# folder = '../scraped_data/pharmacy_current_inventories'
#
# os.makedirs(folder, exist_ok=True)
# timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H_%M')
# filepath = f'{folder}/{pharmacy}_snapshot_{timestamp}.json'
#
# with open(filepath, 'w', encoding='utf-8') as f:
#     json.dump(all_products_json, f, indent=4, ensure_ascii=False)
#
# print(f'Saved current inventory to {filepath}')
#
# # get_available_product_ids