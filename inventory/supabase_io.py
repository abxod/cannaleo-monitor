from typing import Any

import supabase
import json
import logging
from inventory.constants import CONST_SUPABASE_VENDORS_FILE_PATH, CONST_SUPABASE_VENDOR_INVENTORIES_FILE_PATH, \
    CONST_DB_TABLES
from common.retry import with_retry


def load_vendors_information(
    client: supabase.Client,
    file_path: str = CONST_SUPABASE_VENDORS_FILE_PATH, ) -> dict:
    response = with_retry(
        lambda: client.storage.from_(
            'vendors_info_bucket'
        ).download(file_path), None, f'client.storage.from_(\'vendors_info_bucket\').download({file_path})'
        )

    json_str = response.decode('utf-8')
    return json.loads(json_str)


def load_vendor_inventories(
    client: supabase.Client,
    file_path: str = CONST_SUPABASE_VENDOR_INVENTORIES_FILE_PATH, ) -> dict:
    response = client.storage.from_(
        'inventories_bucket'
    ).download(file_path)

    json_str = response.decode('utf-8')
    return json.loads(json_str)


def insert_logs_into_db(
    client: supabase.Client,
    table_name: str,
    events_logs: list[dict], ):
    if table_name not in CONST_DB_TABLES:
        raise ValueError(f'Database table \'{table_name}\' does not exist.')

    if not events_logs:
        return []

    response = client.table(table_name).insert(events_logs).execute()

    return response.data


def upload_to_bucket(
    conn: supabase.Client,
    bucket_name: str,
    file_path: str,
    json_dict: dict, ):
    json_bytes = json.dumps(json_dict).encode('utf-8')

    try:
        response = conn.storage.from_(bucket_name).upload(
            file_path, json_bytes, {
                'upsert': 'true'
            }
            )

        return {
            'success': True,
            'path': response.full_path
        }
    except Exception as e:
        raise


def push_results_to_supabase(client, product_logs: list[dict[str, str | int | float | None]], vendor_logs: list[dict[str, str | int | float | None]], vendor_inventories: dict[str, dict[str, dict[str, float | str]]], all_pid_to_prod_info: dict[str, dict[str, Any]], updated_vendors_information: dict[str, Any]):
    logging.info('Pushing product logs to Supabase.')
    if product_logs:
        try:
            with_retry(
                lambda: insert_logs_into_db(
                    client, 'product_events', product_logs
                ), None, 'insert_logs_into_db(client, \'product_events\', product_logs)'
                )
        except Exception as e:
            logging.error(
                f'Failed to insert product event logs: {e}.', exc_info=True
            )

    logging.info('Pushing vendor logs to Supabase.')
    if vendor_logs:
        try:
            with_retry(lambda: insert_logs_into_db(client, 'vendor_events', vendor_logs), None, 'insert_logs_into_db(client, \'vendor_events\', vendor_logs)')
        except Exception as e:
            logging.error(
                f'Failed to insert vendor event logs: {e}.', exc_info=True
            )

    logging.info('Updating vendor_inventories.json on Supabase.')
    if vendor_inventories:
        try:
            with_retry(
                lambda: upload_to_bucket(
                    client, 'inventories_bucket', 'vendors_inventories.json', vendor_inventories
                ), None, 'upload_to_bucket(client, \'inventories_bucket\', \'vendors_inventories.json\', vendor_inventories)'
                )
        except Exception as e:
            logging.error(
                f'Failed to upload vendor inventories: {e}', exc_info=True
            )

    logging.info('Updating all_products.json on Supabase.')
    if all_pid_to_prod_info:
        try:
            with_retry(
                lambda: upload_to_bucket(
                    client, 'all_products_bucket', 'all_current_products.json', all_pid_to_prod_info
                ), None, 'upload_to_bucket(client, \'all_products_bucket\', \'all_current_products.json\', all_pid_to_prod_info)'
                )
        except Exception as e:
            logging.error(f'Failed to upload all products: {e}', exc_info=True)

    if updated_vendors_information:
        try:
            with_retry(
                lambda: upload_to_bucket(
                    client, 'vendors_info_bucket', 'vendors_information.json', updated_vendors_information
                ), None, 'upload_to_bucket(client, \'vendors_info_bucket\', \'vendors_information.json, updated_vendors_information)'
                )
        except Exception as e:
            logging.error(
                f'Failed to update vendors\' information: {e}', exc_info=True
            )
