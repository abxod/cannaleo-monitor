import logging
import os
import sys
import time
from pathlib import Path

from constants import CONST_SUPABASE_IMAGE_CACHE_TABLE, MAX_RETRIES
from helpers import get_image_cache_rows, process_and_upload_image
from supabase import create_client

from common.indexing import deep_get
from inventory.constants import (
    CONST_SUPABASE_PID_TO_INFO_BUCKET,
    CONST_SUPABASE_PID_TO_INFO_FP,
)
from inventory.supabase_io import load_json_from_bucket

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

log_path = Path.cwd() / "execution_logs.log"

logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def run(
    conn,
):
    logging.info("Starting fetch of product info from Supabase")
    try:
        pid_to_info = load_json_from_bucket(
            conn, CONST_SUPABASE_PID_TO_INFO_BUCKET, CONST_SUPABASE_PID_TO_INFO_FP
        )
    except Exception as e:
        logging.error(f"Failed to fetch vendor information from Supabase: {e}")
        sys.exit(1)

    response = get_image_cache_rows(conn)

    # PIDs which have been seen before but the image for which has been or not been persisted.
    seen_pids = {int(x["pid"]) for x in response}

    # PIDs whose image attribute is missing but can still be retried.
    pids_to_process = {
        int(x["pid"]): x["retry_count"]
        for x in response
        if x.get("retry_count") is not None and int(x["retry_count"]) < MAX_RETRIES
    }

    # New PIDs
    pids_to_process.update(
        {
            pid: None
            for pid in map(int, pid_to_info.keys())
            if deep_get(pid_to_info[str(pid)], "image", "data", "attributes", "img_url")
            is not None
            and pid not in seen_pids
            and pid not in pids_to_process
        }
    )

    missing_img_rows = []
    persisted_img_rows = []
    for pid, retry_count in pids_to_process.items():
        img_url = deep_get(
            pid_to_info, str(pid), "image", "data", "attributes", "img_url"
        )
        if not img_url:
            logging.info(f"PID {pid} does not have an image. Updating retry count.")
            missing_img_rows.append({"pid": pid, "retry_count": (retry_count or 0) + 1})
            continue

        success = process_and_upload_image(pid, img_url, conn)
        if success:
            persisted_img_rows.append({"pid": pid, "retry_count": None})
        else:
            missing_img_rows.append({"pid": pid, "retry_count": (retry_count or 0) + 1})

        time.sleep(2)

    logging.info(
        f"Inserting PIDs with a persisted image into {CONST_SUPABASE_IMAGE_CACHE_TABLE} table."
    )
    try:
        conn.table(CONST_SUPABASE_IMAGE_CACHE_TABLE).upsert(
            json=persisted_img_rows, on_conflict="pid"
        ).execute()
    except Exception as e:
        logging.error(f"Failed to push PIDs with uploaded image rows to table: {e}")

    logging.info(
        f"Inserting PIDs without image into {CONST_SUPABASE_IMAGE_CACHE_TABLE} table."
    )
    try:
        conn.table(CONST_SUPABASE_IMAGE_CACHE_TABLE).upsert(
            json=missing_img_rows, on_conflict="pid"
        ).execute()
    except Exception as e:
        logging.error(f"Failed to push PIDs with missing image rows to table: {e}")


if __name__ == "__main__":
    logging.info("Starting script")
    logging.info("Creating Supabase client")
    conn = create_client(SUPABASE_URL, SUPABASE_KEY)
    run(conn)
    logging.info("Terminating script")
