# Tahoe Kings API

Flask API for [Tahoe Kings](https://tahoekings.com), a used-car inventory site. The React app is in [dealership-frontend](https://github.com/DGoble22/dealership-frontend).

This service replaced an earlier PHP API. That code is still in `legacy_php/` for reference. The live API runs on Render and uses MySQL.

## What it does

- Lists vehicles for the public site, and leaves sold and hidden cars out of those responses.
- Registers and logs in users with PBKDF2-SHA256 password hashes and signed JWTs. Roles are `user` and `admin`.
- Lets an admin add, update, and delete vehicles and photos.
- Stores photos on ImgBB. Each photo keeps a focal point so the storefront can crop around the car.
- Sends contact mail, new-listing notices, and unsubscribe links through Resend.
- Supports password change and email password reset.

## Stack

Python, Flask, PyMySQL, Gunicorn, Pillow, and Resend.

## Run it locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the repo root:

```bash
DB_HOST=localhost
DB_PORT=3306
DB_USER=
DB_PASSWORD=
DB_NAME=
JWT_SECRET_KEY=
RESEND_API_KEY=
IMGBB_API_KEY=
CORS_ALLOWED_ORIGINS=http://localhost:5173
PORT=5000
FLASK_DEBUG=1
```

`IMGBB_API_KEY_DEV` and `IMGBB_API_KEY_PROD` override `IMGBB_API_KEY` when they are set. `CORS_ALLOWED_ORIGINS` is a comma-separated list. Use `*` to allow any origin.

The table definitions are in `sql/table.sql`.

```bash
python app.py
```

`GET /` returns `{"status":"ok"}`.

## API groups

| Prefix | Purpose |
| --- | --- |
| `/api` | Vehicles and images |
| `/api/auth` | Register, login, current user, password change and reset |
| `/api/user` | Profile and email preferences |
| `/api/admin` | Admin identity |
| `/api/mail` | Contact form, new-vehicle notices, unsubscribe |

## Tests

```bash
python -m unittest tests/test_storage.py
```
