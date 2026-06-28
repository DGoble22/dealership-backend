from flask import Blueprint, jsonify, request
import os
import pymysql
from PIL import Image, ImageOps
from .utils import db_conn, uploads_dir, uploads_url, api_error
from .auth import admin_required, decode_access_token


cars_bp = Blueprint('cars_bp', __name__)


def _request_is_admin():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False

    token = auth_header.split(" ", 1)[1]
    payload = decode_access_token(token)
    if not payload:
        return False

    return str(payload.get("role") or "").strip().lower() == "admin"


@cars_bp.route('/get_cars', methods=['GET'])
def get_cars():
    try:
        is_admin = _request_is_admin()
        with db_conn() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            query = """SELECT c.*, p.image_path
                        FROM car c
                        LEFT JOIN pictures p
                        ON c.carid = p.carid AND p.is_main = 1"""

            values = []
            if not is_admin:
                query += " WHERE LOWER(c.status) NOT IN ('sold', 'hidden')"

            query += " ORDER BY c.carid DESC"

            if values:
                cursor.execute(query, tuple(values))
            else:
                cursor.execute(query)
            cars = cursor.fetchall()

        for car in cars:
            image_path = car.get("image_path")
            if image_path:
                car["image_path"] = uploads_url(os.path.basename(image_path))
            else:
                car["image_path"] = uploads_url("default_car_image.jpg")

        return jsonify({"status": "success", "data": cars}), 200
    except Exception as e:
        return api_error(e)


@cars_bp.route('/get_car_by_id', methods=['GET'])
def get_car_by_id(carid=None):
    if carid is None:
        carid = request.args.get('id')

    if carid is None or carid == "":
        return jsonify({"status": "error", "message": "Missing id parameter"}), 400

    try:
        carid = int(carid)
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid id"}), 400

    try:
        is_admin = _request_is_admin()
        with db_conn() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM car WHERE carid = %s", (carid,))
            result = cursor.fetchone()

        if result:
            status = str(result.get("status") or "").strip().lower()
            if not is_admin and status in {"sold", "hidden"}:
                return jsonify({"status": "error", "message": "Car not found"}), 404

            return jsonify({"status": "success", "data": result}), 200
        return jsonify({"status": "error", "message": "Car not found"}), 404
    
    except Exception as e:
        return api_error(e)


@cars_bp.route('/get_car_images', methods=['GET'])
def get_car_images():
    carid = request.args.get('carid')

    if carid is None or carid == "":
        return jsonify({"status": "error", "message": "Missing carid parameter"}), 400

    try:
        carid = int(carid)
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid carid"}), 400

    try:
        is_admin = _request_is_admin()
        with db_conn() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT status FROM car WHERE carid = %s", (carid,))
            car = cursor.fetchone()
            if not car:
                return jsonify({"status": "error", "message": "Car not found"}), 404

            status = str(car.get("status") or "").strip().lower()
            if not is_admin and status in {"sold", "hidden"}:
                return jsonify({"status": "error", "message": "Car not found"}), 404

            cursor.execute("SELECT picid, image_path, is_main, picNo FROM pictures WHERE carid = %s ORDER BY picNo", (carid,))
            result = cursor.fetchall()

        for image in result:
            image_path = image.get("image_path")
            if image_path:
                image["image_path"] = uploads_url(os.path.basename(image_path))
            else:
                image["image_path"] = uploads_url("default_car_image.jpg")

        return jsonify({"status": "success", "data": result}), 200
    except Exception as e:
        return api_error(e)


@cars_bp.route('/add_car', methods=['POST'])
@admin_required
def add_car():
    try:
        payload = request.form if request.form else (request.get_json(silent=True) or {})
        make = payload.get('make')
        model = payload.get('model')
        trim = payload.get('trim')
        year = payload.get('year')
        miles = payload.get('miles')
        price = payload.get('price')
        vin = payload.get('vin')
        color = payload.get('color')
        drivetype = payload.get('drivetype')
        status = payload.get('status')
        description = payload.get('description')

        if not all([make, model, trim, year, miles, price, vin, color, drivetype, status, description]):
            return jsonify({"status": "error", "message": "Missing required fields."}), 400

        valid_drivetypes = {'FWD', 'RWD', 'AWD', '4WD'}
        if drivetype not in valid_drivetypes:
            return jsonify({"status": "error", "message": "Invalid drivetype"}), 400

        try:
            year = int(year)
            miles = int(miles)
            price = float(price)
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid number"}), 400

        with db_conn() as conn:
            cursor = conn.cursor()
            query = "INSERT INTO car (make, model, trim, year, miles, price, vin, color, drivetype, status, description) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(query, (make, model, trim, year, miles, price, vin, color, drivetype, status, description))
            new_car_id = cursor.lastrowid
            conn.commit()

        return jsonify({"status": "success", "message": "Car added successfully!", "carid": new_car_id}), 201
    except Exception as e:
        return api_error(e)


@cars_bp.route('/update_car', methods=['POST'])
@admin_required
def update_car():
    payload = request.get_json(silent=True, force=True) or request.form or {}

    carid = payload.get('carid')
    if carid is None or carid == "":
        return jsonify({"status": "error", "message": "Car id is required"}), 400

    try:
        carid = int(carid)
    except ValueError:
        return jsonify({"status": "error", "message": "Car id integer expected"}), 400

    fields = []
    values = []
    int_fields = {'year', 'miles'}
    float_fields = {'price'}
    string_fields = {'make', 'model', 'trim', 'vin', 'status', 'description', 'color', 'drivetype'}

    for field in [*string_fields, *int_fields, *float_fields]:
        if field not in payload:
            continue

        value = payload.get(field)
        if value is None or value == "":
            continue

        if field in int_fields:
            try:
                value = int(value)
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid number for: " + field}), 400
        elif field in float_fields:
            try:
                value = float(value)
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid number for: " + field}), 400
        else:
            value = str(value).strip()
            if field == 'drivetype' and value not in {'FWD', 'RWD', 'AWD', '4WD'}:
                return jsonify({"status": "error", "message": "Invalid drivetype"}), 400

        fields.append(field + " = %s")
        values.append(value)

    if not fields:
        return jsonify({"status": "error", "message": "No valid fields to update"}), 400

    values.append(carid)

    try:
        with db_conn() as conn:
            cursor = conn.cursor()
            query = "UPDATE car SET " + ", ".join(fields) + " WHERE carid = %s"
            cursor.execute(query, tuple(values))
            if cursor.rowcount > 0:
                conn.commit()
                return jsonify({"status": "success", "message": "Car updated successfully"}), 200
            conn.commit()
            return jsonify({"status": "error", "message": "No Changes Made"}), 200
        
    except Exception as e:
        return api_error(e)


@cars_bp.route('/delete_car', methods=['POST'])
@admin_required
def delete_car():
    payload = request.get_json(silent=True, force=True) or request.form or {}

    carid = payload.get('carid')
    if carid is None or carid == "":
        return jsonify({"status": "error", "message": "Missing id"}), 400

    try:
        carid = int(carid)
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid carid"}), 400

    try:
        with db_conn() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT image_path FROM pictures WHERE carid = %s", (carid,))
            images = cursor.fetchall()
            cursor.execute("DELETE FROM car WHERE carid = %s LIMIT 1", (carid,))
            if cursor.rowcount == 0:
                return jsonify({"status": "error", "message": "Car not found"}), 404
            conn.commit()

        for image in images:
            filename = os.path.basename(image.get('image_path') or '')
            local_path = os.path.join(uploads_dir(), filename)
            if filename and os.path.exists(local_path):
                os.remove(local_path)

        return jsonify({"status": "success", "message": "Car deleted"}), 200
    
    except Exception as e:
        return api_error(e)


@cars_bp.route('/delete_image', methods=['POST'])
@admin_required
def delete_image():
    payload = request.get_json(silent=True, force=True) or request.form or {}

    carid = payload.get('carid')
    picid = payload.get('picid')
    if carid is None or carid == "" or picid is None or picid == "":
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    try:
        carid = int(carid)
        picid = int(picid)
    except ValueError:
        return jsonify({"status": "error", "message": "Integer expected"}), 400

    try:
        with db_conn() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT image_path, is_main FROM pictures WHERE picid = %s", (picid,))
            img = cursor.fetchone()
            if not img:
                return jsonify({"status": "error", "message": "Image not found"}), 404

            cursor.execute("SELECT picid FROM pictures WHERE carid = %s AND picid != %s ORDER BY picid LIMIT 1", (carid, picid))
            next_image = cursor.fetchone()

            cursor.execute("DELETE FROM pictures WHERE picid = %s LIMIT 1", (picid,))
            if cursor.rowcount == 0:
                return jsonify({"status": "error", "message": "Image not found"}), 404

            if int(img.get("is_main") or 0) == 1 and next_image:
                cursor.execute("UPDATE pictures SET is_main = 1 WHERE picid = %s", (next_image["picid"],))

            conn.commit()

        filename = os.path.basename(img.get('image_path') or '')
        local_path = os.path.join(uploads_dir(), filename)
        if filename and os.path.exists(local_path):
            os.remove(local_path)

        return jsonify({"status": "success", "message": "Image deleted"}), 200
    except Exception as e:
        return api_error(e)


@cars_bp.route('/set_is_main', methods=['POST'])
@admin_required
def set_is_main():
    payload = request.get_json(silent=True, force=True) or request.form or {}

    carid = payload.get('carid')
    picid = payload.get('picid')
    if carid is None or picid is None:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    try:
        carid = int(carid)
        picid = int(picid)
    except ValueError:
        return jsonify({"status": "error", "message": "Integer expected"}), 400

    try:
        with db_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE pictures SET is_main = 0 WHERE carid = %s", (carid,))
            cursor.execute("UPDATE pictures SET is_main = 1 WHERE picid = %s", (picid,))
            conn.commit()
        return jsonify({"status": "success", "message": "Cover image updated"}), 200
    except Exception as e:
        return api_error(e)


@cars_bp.route('/add_single_image', methods=['POST'])
@admin_required
def add_single_image():
    carid = request.form.get('carid')
    image = request.files.get('image')
    if carid is None or carid == "" or image is None:
        return jsonify({"status": "error", "message": "Missing car ID or image"}), 400

    try:
        carid = int(carid)
    except ValueError:
        return jsonify({"status": "error", "message": "Missing car ID or image"}), 400

    if image.mimetype not in ['image/jpeg', 'image/png', 'image/gif']:
        return jsonify({"status": "error", "message": "Unsupported image type"}), 400

    try:
        focal_x = max(0.0, min(100.0, float(request.form.get('focal_x', 50))))
        focal_y = max(0.0, min(100.0, float(request.form.get('focal_y', 50))))
    except (ValueError, TypeError):
        focal_x, focal_y = 50.0, 50.0

    try:
        with db_conn() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT MAX(picNo) AS maxNo FROM pictures WHERE carid = %s", (carid,))
            row = cursor.fetchone() or {}
            pic_no = (row.get('maxNo') or 0) + 1
            is_main = 1 if pic_no == 1 else 0

            # Insert first to get the auto-increment picid — used in the filename
            # so every upload gets a unique URL that is never reused after deletion.
            cursor.execute(
                "INSERT INTO pictures (carid, picNo, image_path, is_main, focal_x, focal_y) VALUES (%s, %s, %s, %s, %s, %s)",
                (carid, pic_no, '', is_main, focal_x, focal_y)
            )
            new_pic_id = cursor.lastrowid

            filename = f"car_{carid}_{new_pic_id}.jpg"
            upload_path = os.path.join(uploads_dir(), filename)
            image.save(upload_path)

            # Compress: honour EXIF rotation, resize to max 1600px, re-save as JPEG at 82%
            img = Image.open(upload_path)
            img = ImageOps.exif_transpose(img)
            img = img.convert('RGB')
            if img.width > 1600 or img.height > 1600:
                img.thumbnail((1600, 1600), Image.LANCZOS)
            img.save(upload_path, 'JPEG', quality=90, optimize=True)
            img.close()

            db_path = uploads_url(filename)
            cursor.execute("UPDATE pictures SET image_path = %s WHERE picid = %s", (db_path, new_pic_id))
            conn.commit()

        return jsonify({
            "status": "success",
            "data": {
                "picid": new_pic_id,
                "image_path": db_path,
                "is_main": is_main
            }
        }), 201
    except Exception as e:
        return api_error(e)
    
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return jsonify({"status": "error", "message": str(e)}), 500