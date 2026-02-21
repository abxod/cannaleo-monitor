import supabase
import json
import logging
from constants import CONST_SUPABASE_VENDORS_FILE_PATH, CONST_SUPABASE_VENDOR_INVENTORIES_FILE_PATH, \
    CONST_DB_TABLES
from common.retry import with_retry


def load_vendors_information(
    client: supabase.Client,
    file_path: str = CONST_SUPABASE_VENDORS_FILE_PATH, ) -> dict:
    response = with_retry(
        lambda: client.storage.from_(
            'vendors_info_bucket'
        ).download(file_path)
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