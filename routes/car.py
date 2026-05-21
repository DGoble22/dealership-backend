from flask import Blueprint, jsonify, request
import pymysql


cars_bp = Blueprint('cars_bp', __name__)


@cars_bp.route('/get_cars', methods=['GET'])
def get_cars():
    from app import get_db_connection
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        query = """SELECT c.*, p.image_path 
                    FROM Car c 
                    LEFT JOIN Pictures p 
                    ON c.carid = p.carid AND p.is_main = 1"""

        cursor.execute(query)
        cars = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({"status": "success", "data": cars}), 200
    except Exception as e:
        return jsonify({"status": "error", "data": [], "error": str(e)}), 500
    
@cars_bp.route('/get_car/<int:carid>', methods=['GET'])


@cars_bp.route('/add_car', methods=['POST'])
def add_car():
    from app import get_db_connection
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        payload = request.get_json()
        make = payload.get('make')
        model = payload.get('model')
        trim = payload.get('trim')
        vin = payload.get('vin')
        status = payload.get('status')
        description = payload.get('description')
        year = payload.get('year')
        miles = payload.get('miles')
        price = payload.get('price')
        color = payload.get('color')

        if not all([make, model, trim, vin, status, description, year, miles, price, color]):
            return jsonify({"status": "error", "message": "Missing required fields."}), 400

        query = "INSERT INTO Car (make, model, trim, vin, status, description, year, miles, price, color) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (make, model, trim, vin, status, description, year, miles, price, color))
        conn.commit()

        cursor.close()
        conn.close()
        return jsonify({"status": "success", "message": "Car added successfully!"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": "Failed to add car.", "error": str(e)}), 500