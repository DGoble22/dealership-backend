import os
import pymysql
from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from routes.car import cars_bp
from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.user import user_bp
from routes.mail import mail_bp

load_dotenv()

app = Flask(__name__, static_folder="uploads", static_url_path="/uploads")

raw_allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", "*")
if raw_allowed_origins and raw_allowed_origins.strip() != "*":
    allowed_origins = [origin.strip() for origin in raw_allowed_origins.split(",") if origin.strip()]
else:
    allowed_origins = "*"

app.config["CORS_ALLOWED_ORIGINS"] = allowed_origins
CORS(
    app,
    resources={r"/*": {"origins": app.config["CORS_ALLOWED_ORIGINS"]}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
)

@app.route("/", methods=["GET", "HEAD"])
def health_root():
    return jsonify({"status": "ok"}), 200

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
app.register_blueprint(mail_bp, url_prefix='/api/mail')


if __name__ == "__main__":
	app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "0") == "1")