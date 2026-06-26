from flask import Blueprint, g, jsonify

from .auth import require_auth

user_bp = Blueprint('user_bp', __name__)


@user_bp.route('/me', methods=['GET'])
@require_auth()
def user_me():
	return jsonify({"status": "success", "user": g.current_user}), 200