import base64
from functools import wraps
from datetime import datetime, timedelta
import hashlib
import hmac
import json
import os
import re
import secrets
import time

from flask import Blueprint, g, request, jsonify
import resend

from .utils import db_conn, api_error

auth_bp = Blueprint('auth_bp', __name__)
PASSWORD_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$")
EMAIL_REGEX = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
PASSWORD_RESET_TOKEN_TTL_MINUTES = 30


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


def _ensure_password_reset_table():
	with db_conn() as conn:
		cursor = conn.cursor()
		cursor.execute(
			"""
			CREATE TABLE IF NOT EXISTS password_reset_tokens (
				token_hash CHAR(64) NOT NULL PRIMARY KEY,
				userid INT NOT NULL,
				email VARCHAR(255) NOT NULL,
				created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
				expires_at DATETIME NOT NULL,
				used_at DATETIME NULL,
				INDEX idx_password_reset_userid (userid),
				INDEX idx_password_reset_email (email),
				INDEX idx_password_reset_expires_at (expires_at),
				CONSTRAINT fk_password_reset_user FOREIGN KEY (userid) REFERENCES users(userid) ON DELETE CASCADE
			) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
			"""
		)
		conn.commit()


def _password_reset_token_hash(token):
	return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _site_url():
	return (os.getenv("SITE_URL") or "http://localhost:5173").rstrip("/")


def _send_password_reset_email(recipient_email, reset_url):
	resend.api_key = os.getenv("RESEND_API_KEY", "")
	if not resend.api_key:
		raise RuntimeError("Mail not configured")

	resend.Emails.send({
		"from": "Tahoe Kings <noreply@tahoekings.com>",
		"to": recipient_email,
		"subject": "Reset your Tahoe Kings password",
		"html": f"""
		<div style="font-family:sans-serif;max-width:600px;margin:auto;background:#f9f9f9;border-radius:12px;overflow:hidden;">
		  <div style="background:linear-gradient(135deg,#0f172a,#1d3557);padding:24px 32px;">
		    <h1 style="color:white;margin:0;font-size:1.4rem;">Tahoe Kings</h1>
		    <p style="color:rgba(255,255,255,0.75);margin:4px 0 0;">Password reset requested</p>
		  </div>
		  <div style="padding:28px 32px;color:#1f2937;">
		    <p style="margin:0 0 16px;">We received a request to reset the password for this account.</p>
		    <p style="margin:0 0 24px;">Use the link below to choose a new password. This link expires in 30 minutes.</p>
		    <a href="{reset_url}" style="display:inline-block;background:#163a63;color:white;padding:12px 28px;border-radius:999px;text-decoration:none;font-weight:600;">Reset Password</a>
		    <p style="margin:24px 0 0;color:#6b7280;font-size:0.9rem;word-break:break-all;">If the button does not work, copy and paste this link into your browser:<br/>{reset_url}</p>
		  </div>
		</div>
		""",
	})


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


@auth_bp.route('/change-password', methods=['POST'])
@require_auth()
def change_password():
	payload = request.get_json(silent=True) or {}
	current_password = str(payload.get("currentPassword") or payload.get("current_password") or "")
	new_password = str(payload.get("newPassword") or payload.get("new_password") or "")

	if not current_password or not new_password:
		return jsonify({"status": "error", "message": "Current password and new password are required"}), 400

	password_error = _validate_password_policy(new_password)
	if password_error:
		return jsonify({"status": "error", "message": password_error}), 400

	try:
		with db_conn() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"SELECT userid, password FROM users WHERE userid = %s LIMIT 1",
				(g.current_user["userid"],),
			)
			user = cursor.fetchone()

			if not user:
				return jsonify({"status": "error", "message": "User not found"}), 404

			stored_password = user.get("password", "")
			password_ok = _verify_password(current_password, stored_password)

			# Legacy support for unhashed passwords kept for backward compatibility.
			if not password_ok and stored_password and "$" not in stored_password:
				password_ok = hmac.compare_digest(stored_password, current_password)

			if not password_ok:
				return jsonify({"status": "error", "message": "Current password is incorrect"}), 401

			if _verify_password(new_password, stored_password):
				return jsonify({"status": "error", "message": "New password must be different from current password"}), 400

			cursor.execute(
				"UPDATE users SET password = %s WHERE userid = %s",
				(_generate_password_hash(new_password), g.current_user["userid"]),
			)
			conn.commit()

		return jsonify({"status": "success", "message": "Password updated successfully"}), 200
	except Exception as e:
		return api_error(e)


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
	payload = request.get_json(silent=True) or {}
	email = str(payload.get("email") or "").strip().lower()

	if not email:
		return jsonify({"status": "error", "message": "Email is required"}), 400

	if not EMAIL_REGEX.match(email):
		return jsonify({"status": "error", "message": "Invalid email address"}), 400

	try:
		_ensure_password_reset_table()
		with db_conn() as conn:
			cursor = conn.cursor()
			cursor.execute("SELECT userid, email FROM users WHERE email = %s LIMIT 1", (email,))
			user = cursor.fetchone()

			if not user:
				return jsonify({"status": "success", "message": "If an account exists for that email, reset instructions have been sent."}), 200

			raw_token = secrets.token_urlsafe(32)
			token_hash = _password_reset_token_hash(raw_token)
			expires_at = datetime.utcnow() + timedelta(minutes=PASSWORD_RESET_TOKEN_TTL_MINUTES)

			cursor.execute("DELETE FROM password_reset_tokens WHERE userid = %s", (user["userid"],))
			cursor.execute(
				"INSERT INTO password_reset_tokens (token_hash, userid, email, expires_at) VALUES (%s, %s, %s, %s)",
				(token_hash, user["userid"], user["email"], expires_at),
			)
			conn.commit()

		reset_url = f"{_site_url()}/#/reset-password?token={raw_token}"
		try:
			_send_password_reset_email(user["email"], reset_url)
		except Exception:
			with db_conn() as conn:
				cursor = conn.cursor()
				cursor.execute("DELETE FROM password_reset_tokens WHERE token_hash = %s", (token_hash,))
				conn.commit()
			raise

		return jsonify({"status": "success", "message": "If an account exists for that email, reset instructions have been sent."}), 200
	except Exception as e:
		return api_error(e, "Failed to send reset email")


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
	payload = request.get_json(silent=True) or {}
	token = str(payload.get("token") or "").strip()
	new_password = str(payload.get("newPassword") or payload.get("new_password") or "")
	confirm_password = str(payload.get("confirmPassword") or payload.get("confirm_password") or "")

	if not token or not new_password or not confirm_password:
		return jsonify({"status": "error", "message": "Token, new password, and confirm password are required"}), 400

	if new_password != confirm_password:
		return jsonify({"status": "error", "message": "Passwords do not match"}), 400

	password_error = _validate_password_policy(new_password)
	if password_error:
		return jsonify({"status": "error", "message": password_error}), 400

	token_hash = _password_reset_token_hash(token)

	try:
		with db_conn() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"""
				SELECT token_hash, userid, email
				FROM password_reset_tokens
				WHERE token_hash = %s AND used_at IS NULL AND expires_at > UTC_TIMESTAMP()
				LIMIT 1
				""",
				(token_hash,),
			)
			token_row = cursor.fetchone()

			if not token_row:
				return jsonify({"status": "error", "message": "Invalid or expired reset link"}), 400

			cursor.execute("SELECT userid, password FROM users WHERE userid = %s LIMIT 1", (token_row["userid"],))
			user = cursor.fetchone()
			if not user:
				return jsonify({"status": "error", "message": "Account not found"}), 404

			stored_password = user.get("password", "")
			if _verify_password(new_password, stored_password):
				return jsonify({"status": "error", "message": "New password must be different from the current password"}), 400

			cursor.execute(
				"UPDATE users SET password = %s WHERE userid = %s",
				(_generate_password_hash(new_password), user["userid"]),
			)
			cursor.execute(
				"UPDATE password_reset_tokens SET used_at = UTC_TIMESTAMP() WHERE token_hash = %s AND used_at IS NULL",
				(token_hash,),
			)
			cursor.execute("DELETE FROM password_reset_tokens WHERE userid = %s AND used_at IS NULL", (user["userid"],))
			conn.commit()

		return jsonify({"status": "success", "message": "Password reset successfully"}), 200
	except Exception as e:
		return api_error(e)