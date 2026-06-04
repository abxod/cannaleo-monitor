import io
import logging

import cv2
import numpy as np
import requests
from constants import (
    CONST_RESOLUTION_TO_SUPABASE_STRAIN_IMAGES_FOLDER,
    CONST_SUPABASE_STRAIN_IMAGES_BUCKET,
)
from PIL import Image

from inventory.supabase_io import upload_strain_image_to_supabase

# TODO: This piece of shit file does everything. It imports every library in existence.
# TODO: These libraries aren't needed anywhere else, so it's whatever.


def fetch_image(img_url):
    response = requests.get(img_url)
    img_array = np.frombuffer(response.content, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    return img


def remove_background(img):
    img_bgra = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    lower_white = np.array([200, 200, 200], dtype=np.uint8)
    upper_white = np.array([255, 255, 255], dtype=np.uint8)
    white_mask = cv2.inRange(img, lower_white, upper_white)
    img_bgra[:, :, 3] = np.where(white_mask == 255, 0, 255).astype(np.uint8)

    return img_bgra


def resize_image(img, resolution: tuple):
    resized_img = cv2.resize(img, resolution, interpolation=cv2.INTER_AREA)
    img_object = Image.fromarray(resized_img)
    buf = io.BytesIO()
    img_object.save(buf, format="PNG")
    buf.seek(0)
    return buf


def get_image_cache_rows(conn):
    response = conn.table("image_cache").select("*").execute()
    return response.data


def process_and_upload_image(pid: int, img_url: str, conn) -> bool:
    img = fetch_image(img_url)
    img_bgra = remove_background(img)

    success = True
    for (
        resolution,
        folder,
    ) in CONST_RESOLUTION_TO_SUPABASE_STRAIN_IMAGES_FOLDER.items():
        buf = resize_image(img_bgra, resolution)
        file_path = folder + "/" + str(pid) + ".png"
        try:
            upload_response = upload_strain_image_to_supabase(
                conn, CONST_SUPABASE_STRAIN_IMAGES_BUCKET, file_path, buf
            )
            if upload_response["success"]:
                logging.info(
                    f"Strain image for PID {pid} has been persisted to {upload_response["path"]}."
                )
            else:  # TODO: # Only Supabase should be able to throw an exception. Check for other possible built-in exceptions.
                logging.error(f"Failed to save strain image for PID {pid}.")
            success &= upload_response["success"]
        except Exception as e:
            logging.error(f"Failed to upload strain image for {pid} to Supabase: {e}")
            success = False

    return success
