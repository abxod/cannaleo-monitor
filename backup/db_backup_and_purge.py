import os
import tempfile
from datetime import datetime

import psycopg2
import boto3

DB_URL = os.environ["SUPABASE_DB_URL"]
R2_ACCOUNT_ID = os.environ["R2_ACCOUNT_ID"]
R2_ACCESS_KEY_ID = os.environ["R2_ACCESS_KEY_ID"]
R2_SECRET_ACCESS_KEY = os.environ["R2_SECRET_ACCESS_KEY"]
R2_BUCKET_NAME = os.environ["R2_BUCKET_NAME"]

TABLE_NAME = "inventory_snapshots"
ROW_THRESHOLD = 4_000_000


def get_row_count(cur):
    cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME};")
    return cur.fetchone()[0]


def backup_to_r2(cur, filepath):
    """Dump table to a local CSV file, then upload to Cloudflare R2."""
    print(f"Dumping {TABLE_NAME} to {filepath}...")
    with open(filepath, "w", encoding="utf-8") as f:
        cur.copy_expert(
            f"COPY {TABLE_NAME} TO STDOUT WITH (FORMAT csv, HEADER true)", f
        )

    print("Uploading to Cloudflare R2...")
    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{TABLE_NAME}_backup_{timestamp}.csv"

    s3.upload_file(filepath, R2_BUCKET_NAME, filename)
    print(f"Uploaded: {filename}")


def purge_oldest_rows(cur, conn):
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

    print("Threshold exceeded. Starting backup and purge...")

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as tmp:
        tmp_path = tmp.name

    try:
        backup_to_r2(cur, tmp_path)
        purge_oldest_rows(cur, conn)
    finally:
        os.unlink(tmp_path)
        cur.close()
        conn.close()

    print("Terminating backup script.")


if __name__ == "__main__":
    main()
