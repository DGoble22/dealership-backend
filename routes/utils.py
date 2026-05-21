from contextlib import contextmanager
import logging
import os
from flask import request, jsonify


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


def uploads_url(filename):
    return request.host_url.rstrip("/") + "/uploads/" + filename


def api_error(exc, public_msg="Internal server error", code=500):
    logging.exception("API error: %s", exc)
    return jsonify({"status": "error", "message": public_msg}), code
