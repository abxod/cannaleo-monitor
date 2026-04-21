import os
import json
import tempfile
from datetime import datetime

import psycopg2
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

DB_URL = os.environ["SUPABASE_DB_URL"]
GDRIVE_FOLDER_ID = os.environ["GDRIVE_FOLDER_ID"]
SERVICE_ACCOUNT_INFO = json.loads(os.environ["GDRIVE_SERVICE_ACCOUNT_JSON"])

TABLE_NAME = "inventory_snapshots"
ROW_THRESHOLD = 4_000_000
PURGE_BATCH_SIZE = 50_000


def get_row_count(
    cur,
):
    cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME};")
    return cur.fetchone()[0]


def backup_to_drive(
    cur,
    filepath,
):
    """Dump table to a local CSV file, then upload to Google Drive."""
    print(f"Dumping {TABLE_NAME} to {filepath}...")
    with open(filepath, "w", encoding="utf-8") as f:
        cur.copy_expert(
            f"COPY {TABLE_NAME} TO STDOUT WITH (FORMAT csv, HEADER true)", f
        )

    print("Uploading to Google Drive...")
    creds = service_account.Credentials.from_service_account_info(
        SERVICE_ACCOUNT_INFO,
        scopes=["https://www.googleapis.com/auth/drive.file"],
    )
    service = build("drive", "v3", credentials=creds)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{TABLE_NAME}_backup_{timestamp}.csv"

    file_metadata = {"name": filename, "parents": [GDRIVE_FOLDER_ID]}
    media = MediaFileUpload(filepath, mimetype="text/csv", resumable=True)
    uploaded = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id, name")
        .execute()
    )

    print(f"Uploaded: {uploaded['name']} (ID: {uploaded['id']})")


def purge_oldest_rows(
    cur,
    conn,
):
    total_deleted = 0
    cur.execute(f"TRUNCATE TABLE {TABLE_NAME};")
    conn.commit()
    print(f"Purge complete. Table {TABLE_NAME} emptied.")


def main():
    print("Connecting to database...")
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor()

    row_count = get_row_count(cur)
    print(f"Current row count: {row_count:,}")

    if row_count <= ROW_THRESHOLD:
        print(f"Row count is below threshold ({ROW_THRESHOLD:,}). Nothing to do.")
        return

    print(f"Threshold exceeded. Starting backup and purge...")

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as tmp:
        tmp_path = tmp.name

    try:
        backup_to_drive(cur, tmp_path)
        purge_oldest_rows(cur, conn)
    finally:
        os.unlink(tmp_path)
        cur.close()
        conn.close()

    print("All done.")


if __name__ == "__main__":
    main()
