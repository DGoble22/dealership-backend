from flask import Blueprint, g, jsonify

from .auth import admin_required

admin_bp = Blueprint('admin_bp', __name__)


@admin_bp.route('/me', methods=['GET'])
@admin_required
def admin_me():
	return jsonify({"status": "success", "user": g.current_user}), 200