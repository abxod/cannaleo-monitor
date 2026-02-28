from typing import Any
import supabase
import unicodedata
import json
import logging

from inventory.constants import CONST_SUPABASE_VENDOR_ID_TO_INFO_FP, CONST_SUPABASE_VENDOR_ID_TO_OFFERS_FP
from inventory.constants import CONST_SUPABASE_VENDOR_ID_TO_INFO_BUCKET, CONST_SUPABASE_INVENTORIES_BUCKET, \
    CONST_SUPABASE_PID_TO_INFO_BUCKET, CONST_SUPABASE_VENDOR_ID_TO_INFO_FP, CONST_SUPABASE_VENDOR_ID_TO_OFFERS_FP, \
    CONST_SUPABASE_PID_TO_VENDOR_OFFERS_FP, CONST_SUPABASE_PID_TO_INFO_FP
from inventory.constants import CONST_SUPABASE_PRODUCT_LOGS_TABLE, CONST_SUPABASE_VENDOR_LOGS_TABLE
from common.retry import with_retry


def normalize_strings(
    obj, ):
    if isinstance(obj, str):
        return unicodedata.normalize('NFC', obj)
    if isinstance(obj, dict):
        return {normalize_strings(k): normalize_strings(v) for k, v in obj.items()}
    return obj


# TODO: Generalize the two bottom functions

def load_vendors_information(
    client: supabase.Client,
    file_path: str = CONST_SUPABASE_VENDOR_ID_TO_INFO_FP, ) -> dict:
    response = with_retry(
        lambda: client.storage.from_(
            CONST_SUPABASE_VENDOR_ID_TO_INFO_BUCKET
        ).download(file_path),
        label=f'client.storage.from_(\'{CONST_SUPABASE_VENDOR_ID_TO_INFO_BUCKET}\').download({file_path})'
    )

    json_str = response.decode('utf-8')
    data = json.loads(json_str)
    return normalize_strings(data)


def load_vendor_inventories(
    client: supabase.Client,
    file_path: str = CONST_SUPABASE_VENDOR_ID_TO_OFFERS_FP, ) -> dict:
    response = with_retry(
        lambda: client.storage.from_(
            CONST_SUPABASE_INVENTORIES_BUCKET
        ).download(file_path), label=f'client.storage.from_(\'{CONST_SUPABASE_INVENTORIES_BUCKET}\')'
    )

    json_str = response.decode('utf-8')
    return json.loads(json_str)


def insert_logs_into_db(
    client: supabase.Client,
    table_name: str,
    events_logs: list[dict], ):
    if not events_logs:
        return []

    response = client.table(table_name).insert(events_logs).execute()

    return response.data


def upload_to_bucket(
    conn: supabase.Client,
    bucket_name: str,
    file_path: str,
    json_dict: dict, ):
    json_bytes = json.dumps(json_dict, ensure_ascii=False).encode('utf-8')

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


def push_results_to_supabase(
    client,
    product_logs: list[dict[str, str | int | float | None]],
    vendor_logs: list[dict[str, str | int | float | None]],
    vendor_id_to_offers: dict[str, dict[str, dict[str, float | str]]],
    pid_to_vendors_offers: dict[str, list[dict[str, float | str]]],
    all_pid_to_prod_info: dict[str, dict[str, Any]],
    updated_vendors_information: dict[str, Any], ):
    logging.info('Pushing product logs to Supabase')
    if product_logs:
        try:
            with_retry(
                lambda: insert_logs_into_db(
                    client, CONST_SUPABASE_PRODUCT_LOGS_TABLE, product_logs
                ), label=f'insert_logs_into_db(client, {CONST_SUPABASE_PRODUCT_LOGS_TABLE}, product_logs)'
            )
        except Exception as e:
            logging.error(
                f'Failed to insert product event logs: {e}', exc_info=True
            )

    logging.info('Pushing vendor logs to Supabase')
    if vendor_logs:
        try:
            with_retry(
                lambda: insert_logs_into_db(client, CONST_SUPABASE_VENDOR_LOGS_TABLE, vendor_logs),
                label=f'insert_logs_into_db(client, {CONST_SUPABASE_VENDOR_LOGS_TABLE}, vendor_logs)'
            )
        except Exception as e:
            logging.error(
                f'Failed to insert vendor event logs: {e}', exc_info=True
            )

    logging.info('Updating vendor_id_to_offers.json on Supabase')
    if vendor_id_to_offers:
        try:
            with_retry(
                lambda: upload_to_bucket(
                    client, CONST_SUPABASE_INVENTORIES_BUCKET, CONST_SUPABASE_VENDOR_ID_TO_OFFERS_FP, vendor_id_to_offers
                ),
                label=f'upload_to_bucket(client, {CONST_SUPABASE_INVENTORIES_BUCKET}, {CONST_SUPABASE_VENDOR_ID_TO_OFFERS_FP}, vendor_inventories)'
            )
        except Exception as e:
            logging.error(
                f'Failed to upload vendor inventories: {e}', exc_info=True
            )

    logging.info('Updating pid_to_vendors.json on Supabase')
    if pid_to_vendors_offers:
        try:
            with_retry(
                lambda: upload_to_bucket(
                    client, CONST_SUPABASE_INVENTORIES_BUCKET, CONST_SUPABASE_PID_TO_VENDOR_OFFERS_FP, pid_to_vendors_offers
                ), label=f'upload_to_bucket(client, {CONST_SUPABASE_INVENTORIES_BUCKET}, {CONST_SUPABASE_PID_TO_VENDOR_OFFERS_FP}, pid_to_vendors)'
            )
        except Exception as e:
            logging.error(
                f'Failed to upload pid_to_vendors: {e}', exc_info=True
            )

    logging.info('Updating all_products.json on Supabase')
    if all_pid_to_prod_info:
        try:
            with_retry(
                lambda: upload_to_bucket(
                    client, CONST_SUPABASE_PID_TO_INFO_BUCKET, CONST_SUPABASE_PID_TO_INFO_FP, all_pid_to_prod_info
                ),
                label=f'upload_to_bucket(client, {CONST_SUPABASE_PID_TO_INFO_FP}, {CONST_SUPABASE_PID_TO_INFO_FP}, all_pid_to_prod_info)'
            )
        except Exception as e:
            logging.error(f'Failed to upload all products: {e}', exc_info=True)

    if updated_vendors_information:
        try:
            with_retry(
                lambda: upload_to_bucket(
                    client, CONST_SUPABASE_VENDOR_ID_TO_INFO_BUCKET, CONST_SUPABASE_VENDOR_ID_TO_INFO_FP, updated_vendors_information
                ),
                label=f'upload_to_bucket(client, {CONST_SUPABASE_VENDOR_ID_TO_INFO_BUCKET}, {CONST_SUPABASE_VENDOR_ID_TO_INFO_FP}, updated_vendors_information)'
            )
        except Exception as e:
            logging.error(
                f'Failed to update vendors\' information: {e}', exc_info=True
            )
