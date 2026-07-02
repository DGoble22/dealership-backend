from contextlib import contextmanager
import base64
import json
import logging
import os
import time
from io import BytesIO
from urllib import request as urllib_request
from urllib.parse import urlencode

from PIL import Image, ImageOps
from flask import jsonify


@contextmanager
def db_conn():
    """Context manager that yields a DB connection from app.get_db_connection().
    It will rollback on exception and always close the connection.
    """
    conn = None
    try:
        from app import get_db_connection
        conn = get_db_connection()
        yield conn
    except Exception:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        logging.exception("Database operation failed")
        raise
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def uploads_dir():
    backend_root = os.path.dirname(os.path.dirname(__file__))
    uploads = os.path.join(backend_root, "uploads")
    os.makedirs(uploads, exist_ok=True)
    return uploads


def get_public_base_url():
    return (os.getenv("PUBLIC_BASE_URL") or os.getenv("APP_BASE_URL") or "http://localhost:5001").rstrip("/") + "/"


def uploads_url(filename):
    return get_public_base_url() + "uploads/" + filename


def resolve_image_url(image_path):
    if not image_path:
        return uploads_url("default_car_image.jpg")
    if isinstance(image_path, str) and image_path.startswith(("http://", "https://")):
        return image_path
    return uploads_url(os.path.basename(image_path))


def _get_imgbb_api_key():
    env_name = (os.getenv("APP_ENV") or "development").lower()
    if env_name in {"prod", "production"}:
        return os.getenv("IMGBB_API_KEY_PROD") or os.getenv("IMGBB_API_KEY")
    return os.getenv("IMGBB_API_KEY_DEV") or os.getenv("IMGBB_API_KEY")


def next_picture_number(max_pic_no):
    try:
        return (int(max_pic_no) if max_pic_no is not None else -1) + 1
    except (TypeError, ValueError):
        return 0


def process_image_bytes(image_bytes, content_type=None):
    img = Image.open(BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)
    if img.mode in {"RGBA", "LA", "P"}:
        img = img.convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")

    if img.width > 1600 or img.height > 1600:
        img.thumbnail((1600, 1600), Image.LANCZOS)

    output = BytesIO()
    img.save(output, format="JPEG", quality=90, optimize=True)
    img.close()
    return output.getvalue(), "image/jpeg"


def upload_image(image_file, filename=None, content_type=None):
    if hasattr(image_file, "read"):
        content = image_file.read()
        if not filename and hasattr(image_file, "filename"):
            filename = getattr(image_file, "filename")
    else:
        content = image_file

    if not filename:
        ext = ".jpg"
        if content_type == "image/png":
            ext = ".png"
        elif content_type == "image/gif":
            ext = ".gif"
        filename = f"upload_{int(time.time())}{ext}"

    backend = (os.getenv("IMAGE_STORAGE_BACKEND") or "local").lower()
    if backend == "imgbb":
        api_key = _get_imgbb_api_key()
        if not api_key:
            raise RuntimeError("imgBB API key is not configured")

        encoded = base64.b64encode(content).decode("ascii")
        payload = urlencode({"key": api_key, "image": encoded, "name": filename}).encode("utf-8")
        req = urllib_request.Request(
            "https://api.imgbb.com/1/upload",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib_request.urlopen(req, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))

        if not body.get("success"):
            error_msg = body.get("error", {}).get("message", "imgBB upload failed")
            raise RuntimeError(error_msg)

        image_data = body.get("data", {})
        return {
            "storage": "imgbb",
            "filename": filename,
            "url": image_data.get("url") or image_data.get("display_url"),
            "delete_url": image_data.get("delete_url"),
        }

    upload_dir = uploads_dir()
    upload_path = os.path.join(upload_dir, filename)
    with open(upload_path, "wb") as handle:
        handle.write(content)

    return {
        "storage": "local",
        "filename": filename,
        "url": uploads_url(filename),
    }


def ensure_picture_delete_url_column():
    with db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SHOW COLUMNS FROM pictures LIKE 'delete_url'")
        existing = cursor.fetchone()
        if not existing:
            cursor.execute("ALTER TABLE pictures ADD COLUMN delete_url VARCHAR(500) NULL")
            conn.commit()
            return True
        return False


def delete_image(image_path, delete_url=None):
    if not image_path:
        return {"storage": "none", "deleted": True}

    backend = (os.getenv("IMAGE_STORAGE_BACKEND") or "local").lower()
    if backend == "imgbb" and isinstance(image_path, str) and image_path.startswith(("http://", "https://")):
        if delete_url:
            api_key = _get_imgbb_api_key()
            if api_key:
                req = urllib_request.Request(
                    delete_url,
                    headers={"Content-Type": "application/json"},
                )
                try:
                    with urllib_request.urlopen(req, timeout=15) as response:
                        body = json.loads(response.read().decode("utf-8"))
                    return {"storage": "imgbb", "deleted": bool(body.get("success"))}
                except Exception:
                    logging.exception("imgBB deletion failed")
        return {"storage": "imgbb", "deleted": False}

    if backend != "imgbb":
        filename = os.path.basename(image_path)
        local_path = os.path.join(uploads_dir(), filename)
        if filename and os.path.exists(local_path):
            os.remove(local_path)
        return {"storage": "local", "deleted": True}

    return {"storage": "imgbb", "deleted": False}


def api_error(exc, public_msg="Internal server error", code=500):
    logging.exception("API error: %s", exc)
    return jsonify({"status": "error", "message": public_msg}), code
