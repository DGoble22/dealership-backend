import base64
from functools import wraps
import hashlib
import hmac
import json
import os
import re
import secrets
import time

from flask import Blueprint, g, request, jsonify

from .utils import db_conn, api_error

auth_bp = Blueprint('auth_bp', __name__)
PASSWORD_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$")


def _validate_password_policy(password):
	if not PASSWORD_REGEX.match(password):
		return "Password must be at least 8 characters and include an uppercase letter, a lowercase letter, a number, and a special character"
	return None


def _b64url_encode(raw_bytes):
	return base64.urlsafe_b64encode(raw_bytes).rstrip(b"=").decode("ascii")


def _b64url_decode(encoded_text):
	padding = "=" * (-len(encoded_text) % 4)
	return base64.urlsafe_b64decode(encoded_text + padding)


def _jwt_secret():
	return (os.getenv("JWT_SECRET_KEY") or "change_me").encode("utf-8")


def _generate_password_hash(password):
	iterations = 200000
	salt = secrets.token_hex(16)
	digest = hashlib.pbkdf2_hmac(
		"sha256",
		password.encode("utf-8"),
		bytes.fromhex(salt),
		iterations,
	).hex()
	return f"pbkdf2_sha256${iterations}${salt}${digest}"


def _verify_password(password, stored_hash):
	try:
		algo, iter_text, salt, digest = stored_hash.split("$", 3)
		if algo != "pbkdf2_sha256":
			return False

		check_digest = hashlib.pbkdf2_hmac(
			"sha256",
			password.encode("utf-8"),
			bytes.fromhex(salt),
			int(iter_text),
		).hex()
		return hmac.compare_digest(check_digest, digest)
	except Exception:
		return False


def _create_access_token(user):
	now = int(time.time())
	payload = {
		"sub": str(user["userid"]),
		"email": user["email"],
		"role": user["role"],
		"iat": now,
		"exp": now + (60 * 60 * 24),
	}

	header_json = json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode("utf-8")
	payload_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")

	encoded_header = _b64url_encode(header_json)
	encoded_payload = _b64url_encode(payload_json)
	signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")

	signature = hmac.new(_jwt_secret(), signing_input, hashlib.sha256).digest()
	encoded_signature = _b64url_encode(signature)
	return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def decode_access_token(token):
	try:
		parts = token.split(".")
		if len(parts) != 3:
			return None

		encoded_header, encoded_payload, encoded_signature = parts
		signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
		expected_signature = hmac.new(_jwt_secret(), signing_input, hashlib.sha256).digest()

		if not hmac.compare_digest(_b64url_decode(encoded_signature), expected_signature):
			return None

		payload = json.loads(_b64url_decode(encoded_payload).decode("utf-8"))
		if int(payload.get("exp", 0)) < int(time.time()):
			return None
		return payload
	except Exception:
		return None


def _get_auth_payload_from_request():
	auth_header = request.headers.get("Authorization", "")
	if not auth_header.startswith("Bearer "):
		return None, (jsonify({"status": "error", "message": "Missing bearer token"}), 401)

	token = auth_header.split(" ", 1)[1]
	payload = decode_access_token(token)
	if not payload:
		return None, (jsonify({"status": "error", "message": "Invalid or expired token"}), 401)

	return payload, None


def require_auth(admin_only=False):
	def decorator(fn):
		@wraps(fn)
		def wrapped(*args, **kwargs):
			payload, error_response = _get_auth_payload_from_request()
			if error_response:
				return error_response

			role = str(payload.get("role") or "").strip().lower()
			if admin_only and role != "admin":
				return jsonify({"status": "error", "message": "Admin access required"}), 403

			g.current_user = {
				"userid": payload.get("sub"),
				"email": payload.get("email"),
				"role": payload.get("role"),
			}
			return fn(*args, **kwargs)

		return wrapped

	return decorator


def admin_required(fn):
	return require_auth(admin_only=True)(fn)


@auth_bp.route('/register', methods=['POST'])
def register():
	payload = request.get_json(silent=True) or {}
	email = str(payload.get("email") or "").strip().lower()
	password = str(payload.get("password") or "")
	confirm_password = str(payload.get("confirmPassword") or payload.get("confirm_password") or "")
	receive_emails = payload.get("receiveEmails")
	if receive_emails is None:
		receive_emails = payload.get("receive_emails", False)

	if not email or not password or not confirm_password:
		return jsonify({"status": "error", "message": "Email, password, and confirm password are required"}), 400

	if password != confirm_password:
		return jsonify({"status": "error", "message": "Passwords do not match"}), 400

	password_error = _validate_password_policy(password)
	if password_error:
		return jsonify({"status": "error", "message": password_error}), 400

	try:
		with db_conn() as conn:
			cursor = conn.cursor()
			cursor.execute("SELECT userid FROM users WHERE email = %s LIMIT 1", (email,))
			existing = cursor.fetchone()
			if existing:
				return jsonify({"status": "error", "message": "Email already in use"}), 409

			password_hash = _generate_password_hash(password)
			cursor.execute(
				"INSERT INTO users (email, password, role, receive_emails) VALUES (%s, %s, %s, %s)",
				(email, password_hash, "user", 1 if bool(receive_emails) else 0),
			)
			conn.commit()

		return jsonify({"status": "success", "message": "Registration successful"}), 201
	except Exception as e:
		return api_error(e)


@auth_bp.route('/login', methods=['POST'])
def login():
	payload = request.get_json(silent=True) or {}
	email = str(payload.get("email") or "").strip().lower()
	password = str(payload.get("password") or "")

	if not email or not password:
		return jsonify({"status": "error", "message": "Email and password are required"}), 400

	try:
		with db_conn() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"SELECT userid, email, password, role, receive_emails FROM users WHERE email = %s LIMIT 1",
				(email,),
			)
			user = cursor.fetchone()

		if not user:
			return jsonify({"status": "error", "message": "Invalid email or password"}), 401

		stored_password = user.get("password", "")
		password_ok = _verify_password(password, stored_password)

		# Legacy support: if old plaintext passwords exist, allow once and upgrade to hashed format.
		if not password_ok and stored_password and "$" not in stored_password:
			password_ok = hmac.compare_digest(stored_password, password)
			if password_ok:
				with db_conn() as conn:
					cursor = conn.cursor()
					cursor.execute(
						"UPDATE users SET password = %s WHERE userid = %s",
						(_generate_password_hash(password), user["userid"]),
					)
					conn.commit()

		if not password_ok:
			return jsonify({"status": "error", "message": "Invalid email or password"}), 401

		token = _create_access_token(user)
		return jsonify({
			"status": "success",
			"message": "Login successful",
			"token": token,
			"user": {
				"userid": user["userid"],
				"email": user["email"],
				"role": user["role"],
				"receive_emails": user.get("receive_emails", 0),
			},
		}), 200
	except Exception as e:
		return api_error(e)


@auth_bp.route('/me', methods=['GET'])
def me():
	auth_header = request.headers.get("Authorization", "")
	if not auth_header.startswith("Bearer "):
		return jsonify({"status": "error", "message": "Missing bearer token"}), 401

	token = auth_header.split(" ", 1)[1]
	payload = decode_access_token(token)
	if not payload:
		return jsonify({"status": "error", "message": "Invalid or expired token"}), 401

	return jsonify({
		"status": "success",
		"user": {
			"userid": payload.get("sub"),
			"email": payload.get("email"),
			"role": payload.get("role"),
		},
	}), 200