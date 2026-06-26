import hashlib
import hmac
import os
import re
import pymysql
import resend
from flask import Blueprint, jsonify, request
from .utils import api_error, db_conn
from .auth import admin_required

mail_bp = Blueprint('mail_bp', __name__)

CONTACT_TO = os.getenv('CONTACT_TO_EMAIL', 'contact@tahoekings.com')
FROM_NOREPLY = 'Tahoe Kings <noreply@tahoekings.com>'

_EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')


@mail_bp.route('/contact', methods=['POST'])
def contact():
    data = request.get_json(silent=True, force=True) or {}
    name    = (data.get('name') or '').strip()
    email   = (data.get('email') or '').strip()
    phone   = (data.get('phone') or '').strip()
    message = (data.get('message') or '').strip()
    subject = (data.get('subject') or 'New message from tahoekings.com').strip()

    if not name or not email or not message:
        return jsonify({"status": "error", "message": "Name, email, and message are required"}), 400
    if not _EMAIL_RE.match(email):
        return jsonify({"status": "error", "message": "Invalid email address"}), 400
    if len(name) > 120 or len(email) > 254 or len(message) > 4000:
        return jsonify({"status": "error", "message": "Input too long"}), 400

    resend.api_key = os.getenv('RESEND_API_KEY', '')
    if not resend.api_key:
        return jsonify({"status": "error", "message": "Mail not configured"}), 503

    phone_line = f"<p><strong>Phone:</strong> {phone}</p>" if phone else ""

    try:
        resend.Emails.send({
            "from": FROM_NOREPLY,
            "to": CONTACT_TO,
            "reply_to": email,
            "subject": f"[Tahoe Kings Contact] {subject}",
            "html": f"""
            <div style="font-family:sans-serif;max-width:600px;margin:auto">
                <h2 style="color:#163a63">New Contact Form Submission</h2>
                <p><strong>Name:</strong> {name}</p>
                <p><strong>Email:</strong> <a href="mailto:{email}">{email}</a></p>
                {phone_line}
                <hr style="border:1px solid #e0e0e0"/>
                <p style="white-space:pre-wrap">{message}</p>
            </div>
            """,
        })
        return jsonify({"status": "success", "message": "Message sent"}), 200
    except Exception as e:
        return api_error(e, "Failed to send message")


# ── Subscription helpers ──────────────────────────────────────────────────────

def _unsub_token(userid, email):
    secret = (os.getenv('JWT_SECRET_KEY') or 'change_me').encode()
    sig = hmac.new(secret, f"{userid}:{email}".encode(), hashlib.sha256).hexdigest()
    return f"{userid}.{sig}"


def _verify_unsub_token(token):
    try:
        userid_str, sig = token.split('.', 1)
        userid = int(userid_str)
        with db_conn() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT email FROM Users WHERE userid = %s", (userid,))
            row = cursor.fetchone()
        if not row:
            return None
        expected_sig = _unsub_token(userid, row['email']).split('.', 1)[1]
        if hmac.compare_digest(sig, expected_sig):
            return userid
        return None
    except Exception:
        return None


# ── Notify subscribers of new listing ─────────────────────────────────────────

@mail_bp.route('/notify_new_car', methods=['POST'])
@admin_required
def notify_new_car():
    data = request.get_json(silent=True, force=True) or {}
    try:
        carid = int(data.get('carid', 0))
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Invalid carid"}), 400
    if not carid:
        return jsonify({"status": "error", "message": "carid required"}), 400

    notify_type = data.get('notify_type', 'new')  # "new" or "updated"
    try:
        old_price = float(data['old_price']) if data.get('old_price') is not None else None
    except (ValueError, TypeError):
        old_price = None

    resend.api_key = os.getenv('RESEND_API_KEY', '')
    if not resend.api_key:
        return jsonify({"status": "error", "message": "Mail not configured"}), 503

    site_url = os.getenv('SITE_URL', 'http://localhost:5173').rstrip('/')

    try:
        with db_conn() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM Car WHERE carid = %s", (carid,))
            car = cursor.fetchone()
            if not car:
                return jsonify({"status": "error", "message": "Car not found"}), 404

            cursor.execute("SELECT image_path FROM Pictures WHERE carid = %s AND is_main = 1 LIMIT 1", (carid,))
            img_row = cursor.fetchone()

            cursor.execute("SELECT userid, email FROM Users WHERE receive_emails = 1")
            subscribers = cursor.fetchall()

        if not subscribers:
            return jsonify({"status": "success", "message": "No subscribers to notify", "sent": 0}), 200

        car_url = f"{site_url}/cars/{carid}"
        img_html = (f'<img src="{img_row["image_path"]}" alt="car" style="width:100%;max-height:280px;object-fit:cover;border-radius:8px;margin-bottom:20px;" />'
                    if img_row else "")
        trim = f" {car['trim']}" if car.get('trim') else ""
        new_price = float(car['price'])
        is_price_drop = (old_price is not None and old_price > new_price)

        # ── Build email content based on type ────────────────────────────────
        if notify_type == 'updated':
            if is_price_drop:
                subject = f"Price Drop: {car['year']} {car['make']} {car['model']}{trim} — Now ${new_price:,.0f}"
                header_bg = "linear-gradient(135deg,#b45309,#92400e)"
                header_label = "Price Drop!"
                price_block = f"""
                <div style="background:#fffbeb;border:2px solid #f59e0b;border-radius:10px;padding:16px 20px;margin-bottom:20px;">
                  <p style="color:#92400e;font-weight:700;font-size:0.85rem;margin:0 0 10px;text-transform:uppercase;letter-spacing:0.05em;">Price Reduced</p>
                  <div style="display:flex;align-items:center;gap:18px;flex-wrap:wrap;">
                    <span style="color:#9ca3af;text-decoration:line-through;font-size:1.15rem;">${old_price:,.0f}</span>
                    <span style="color:#15803d;font-size:1.9rem;font-weight:800;line-height:1;">${new_price:,.0f}</span>
                  </div>
                </div>
                <p style="color:#555;margin:0 0 4px;"><strong>Mileage:</strong> {car['miles']:,} mi</p>
                <p style="color:#555;margin:0 0 20px;"><strong>Color:</strong> {car['color']}</p>"""
            else:
                subject = f"Listing Updated: {car['year']} {car['make']} {car['model']}{trim}"
                header_bg = "linear-gradient(135deg,#1e3a5f,#163a63)"
                header_label = "Listing Updated"
                price_block = f"""
                <p style="color:#555;margin:0 0 4px;"><strong>Price:</strong> ${new_price:,.0f}</p>
                <p style="color:#555;margin:0 0 4px;"><strong>Mileage:</strong> {car['miles']:,} mi</p>
                <p style="color:#555;margin:0 0 20px;"><strong>Color:</strong> {car['color']}</p>"""
        else:
            subject = f"New Listing: {car['year']} {car['make']} {car['model']}{trim}"
            header_bg = "linear-gradient(135deg,#0f172a,#1d3557)"
            header_label = "New Vehicle Available"
            price_block = f"""
            <p style="color:#555;margin:0 0 4px;"><strong>Price:</strong> ${new_price:,.0f}</p>
            <p style="color:#555;margin:0 0 4px;"><strong>Mileage:</strong> {car['miles']:,} mi</p>
            <p style="color:#555;margin:0 0 20px;"><strong>Color:</strong> {car['color']}</p>"""

        sent = 0
        errors = 0
        for user in subscribers:
            token = _unsub_token(user['userid'], user['email'])
            unsub_url = f"{site_url}/unsubscribe?token={token}"
            try:
                resend.Emails.send({
                    "from": FROM_NOREPLY,
                    "to": user['email'],
                    "subject": subject,
                    "html": f"""
                    <div style="font-family:sans-serif;max-width:600px;margin:auto;background:#f9f9f9;border-radius:12px;overflow:hidden;">
                      <div style="background:{header_bg};padding:24px 32px;">
                        <h1 style="color:white;margin:0;font-size:1.4rem;">Tahoe Kings</h1>
                        <p style="color:rgba(255,255,255,0.75);margin:4px 0 0;">{header_label}</p>
                      </div>
                      <div style="padding:28px 32px;">
                        {img_html}
                        <h2 style="color:#163a63;margin:0 0 12px;">{car['year']} {car['make']} {car['model']}{trim}</h2>
                        {price_block}
                        <a href="{car_url}" style="display:inline-block;background:#163a63;color:white;padding:12px 28px;border-radius:999px;text-decoration:none;font-weight:600;">View Listing</a>
                      </div>
                      <div style="padding:16px 32px;border-top:1px solid #e0e0e0;text-align:center;">
                        <p style="color:#aaa;font-size:0.76rem;margin:0;">You opted in to vehicle alerts from Tahoe Kings.<br/>
                        <a href="{unsub_url}" style="color:#aaa;">Unsubscribe</a></p>
                      </div>
                    </div>
                    """,
                })
                sent += 1
            except Exception:
                errors += 1

        return jsonify({"status": "success", "message": f"Notified {sent} subscriber{'s' if sent != 1 else ''}", "sent": sent, "errors": errors}), 200
    except Exception as e:
        return api_error(e)


# ── One-click unsubscribe ──────────────────────────────────────────────────────

@mail_bp.route('/unsubscribe', methods=['GET'])
def unsubscribe():
    token = request.args.get('token', '')
    if not token:
        return jsonify({"status": "error", "message": "Missing token"}), 400
    userid = _verify_unsub_token(token)
    if not userid:
        return jsonify({"status": "error", "message": "Invalid unsubscribe link"}), 400
    try:
        with db_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE Users SET receive_emails = 0 WHERE userid = %s", (userid,))
            conn.commit()
        return jsonify({"status": "success", "message": "You've been unsubscribed"}), 200
    except Exception as e:
        return api_error(e)
