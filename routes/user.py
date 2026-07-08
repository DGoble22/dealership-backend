from flask import Blueprint, g, jsonify, request

from .utils import api_error, db_conn

from .auth import require_auth

user_bp = Blueprint('user_bp', __name__)


@user_bp.route('/me', methods=['GET'])
@require_auth()
def user_me():
	return jsonify({"status": "success", "user": g.current_user}), 200


def _coerce_bool(value):
	if isinstance(value, bool):
		return value
	if isinstance(value, (int, float)):
		return value != 0
	if isinstance(value, str):
		return value.strip().lower() in {"1", "true", "yes", "on"}
	return False


@user_bp.route('/preferences', methods=['PATCH'])
@require_auth()
def update_preferences():
	payload = request.get_json(silent=True) or {}
	if "receive_emails" not in payload and "receiveEmails" not in payload:
		return jsonify({"status": "error", "message": "receive_emails is required"}), 400

	receive_emails = payload.get("receive_emails")
	if receive_emails is None:
		receive_emails = payload.get("receiveEmails")

	try:
		with db_conn() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"UPDATE users SET receive_emails = %s WHERE userid = %s",
				(1 if _coerce_bool(receive_emails) else 0, g.current_user["userid"]),
			)
			conn.commit()

			cursor.execute(
				"SELECT userid, email, role, receive_emails FROM users WHERE userid = %s LIMIT 1",
				(g.current_user["userid"],),
			)
			user = cursor.fetchone()

		if not user:
			return jsonify({"status": "error", "message": "User not found"}), 404

		return jsonify({"status": "success", "user": user}), 200
	except Exception as e:
		return api_error(e)