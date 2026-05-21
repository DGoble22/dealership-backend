import os
import pymysql
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from routes.car import cars_bp
from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.user import user_bp

load_dotenv()

app = Flask(__name__, static_folder="uploads", static_url_path="/uploads")
app.config["CORS_ALLOWED_ORIGINS"] = os.getenv("CORS_ALLOWED_ORIGINS", "*")
CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ALLOWED_ORIGINS"]}})

def get_db_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT") or 3306),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        cursorclass=pymysql.cursors.DictCursor
    )

app.register_blueprint(cars_bp, url_prefix='/api')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(user_bp, url_prefix='/api/user')


if __name__ == "__main__":
	app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "0") == "1")