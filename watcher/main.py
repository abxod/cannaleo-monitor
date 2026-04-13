import os
import logging
from pathlib import Path

import supabase
import requests

from inventory.constants import CONST_SUPABASE_NOTIFICATION_SUBSCRIPTIONS_TABLE, CONST_NTFY_PLACEHOLDER_MESSAGE

log_path = Path.cwd() / 'execution_logs.log'
logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_KEY']


def normalize_event_type(
    event_type: str, ):
    match event_type:
        case 'PRODUCT_AVAILABILITY':
            return 'Product Availability'
        case 'PRODUCT_PRICE_CHANGE':
            return 'Product Price Change'
        case 'PRICING_ERROR':
            return 'Price Error'
        case _:
            return 'Event type not recognized.'


def construct_message(
    normalized_event_type: str,
    row: dict, ) -> str:
    match normalized_event_type:
        case 'Product Availability':
            return ''
        case 'Product Price Change':
            return ''
        case 'Price Error':
            return f'{normalized_event_type} ⬇️ : {row['pid']} down to {row['old_price']} from {row['new_price']}'
        case _:
            return 'Event type not recognized.'


# TODO: Move this function elsewhere
def send_ntfy_notification(
    ntfy_topic: str,
    message: str = CONST_NTFY_PLACEHOLDER_MESSAGE, ):
    requests.post(f'https://ntfy.sh/{ntfy_topic}', data=message)


def run(
    client, ):
    notification_subscriptions_response = client.table(CONST_SUPABASE_NOTIFICATION_SUBSCRIPTIONS_TABLE).select('*').eq(
        'enabled',
        True
        ).execute()
    notification_subscriptions = notification_subscriptions_response.data

    if len(notification_subscriptions) == 0:
        logging.info('No NTFY topics to notify')
        return

    # Filter for prices below 1€ in a PostgresSQL function
    pricing_error_rows_response = client.rpc('get_latest_pricing_errors').execute()
    pricing_error_rows = pricing_error_rows_response.data
    if len(pricing_error_rows) == 0:
        logging.info('No pricing errors found.')
        return

    for subscription in notification_subscriptions:
        event_type = subscription['event_type']
        normalized_event_type = normalize_event_type(event_type)
        message = construct_message(normalized_event_type, subscription)
        send_ntfy_notification(subscription['ntfy_topic'], message)

    logging.info('Finished sending out notifications for subscribed events')


if __name__ == '__main__':
    # TODO: Better logs
    logging.info('Starting notification system')
    client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
    run(client)
    logging.info('Terminating notification system')
