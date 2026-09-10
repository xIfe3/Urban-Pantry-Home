# Deploying Urban Pantry to cPanel (MySQL + Passenger)

This project is now configured to run either locally (SQLite, `DEBUG=True`,
no env file needed) or in production on cPanel (MySQL, `DEBUG=False`, driven
entirely by environment variables). Nothing about local dev changes — this
only adds a production path.

## 1. Create the MySQL database

In cPanel → **MySQL Databases**:

1. Create a database, e.g. `cpaneluser_urbanpantry`.
2. Create a database user with a strong password.
3. Add that user to the database with **All Privileges**.

Keep the full database name, username, and password — you'll need them below.
cPanel prefixes both the database and user with your cPanel username
(`cpaneluser_...`), which is normal.

## 2. Upload the code

Upload the project (everything in this folder) to somewhere like
`/home/cpaneluser/urbanpantry/` — outside `public_html`, since Passenger
serves the app directly and `public_html` isn't needed for the app itself.

Do **not** upload `venv/`, `db.sqlite3`, or a real `.env` — see
[.gitignore](.gitignore). If you're using git, `git clone`/`git pull`
directly on the server via cPanel's Git Version Control tool is simplest.

## 3. Create the Python App

In cPanel → **Setup Python App**:

1. Python version: 3.11+ (match what you develop with).
2. Application root: the folder you uploaded to, e.g. `urbanpantry`.
3. Application URL: your domain or subdomain.
4. Application startup file: `passenger_wsgi.py`
5. Application Entry point: `application`
6. Click **Create**.

cPanel creates a dedicated virtualenv and gives you an "Enter to the virtual
environment" command — run that, then from the project root:

```bash
pip install -r requirements.txt
```

## 4. Configure environment variables

Still in **Setup Python App**, scroll to **Environment variables** and add
each of these (see [.env.example](.env.example) for the full list and
explanations):

| Variable | Value |
|---|---|
| `DJANGO_SECRET_KEY` | a long random string (generate one, don't reuse the dev key) |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_ALLOWED_HOSTS` | `yourdomain.com,www.yourdomain.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://yourdomain.com,https://www.yourdomain.com` |
| `DB_ENGINE` | `mysql` |
| `DB_NAME` | the database name from step 1 |
| `DB_USER` | the database user from step 1 |
| `DB_PASSWORD` | the database password from step 1 |
| `DB_HOST` | `localhost` |
| `DB_PORT` | `3306` |
| `DJANGO_SESSION_COOKIE_SECURE` | `True` (once HTTPS is live) |
| `DJANGO_CSRF_COOKIE_SECURE` | `True` (once HTTPS is live) |

Add email/Paystack vars too if you use those features in production.

Alternatively, copy `.env.example` to `.env` in the project root and fill it
in — `settings.py` loads it automatically via `python-dotenv` if present.
Either approach works; env vars set directly in cPanel take precedence.

## 5. Run migrations and collect static files

From the "Enter to the virtual environment" shell, in the project root:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

`collectstatic` writes into `staticfiles/` (or wherever `DJANGO_STATIC_ROOT`
points). WhiteNoise serves everything under that folder directly from the
Django process, so no separate Apache static config is required.

## 6. Media uploads (product images, etc.)

Media files (things uploaded through the admin, e.g. product photos) are
**not** handled by WhiteNoise — only static assets are. By default they're
written to `media/` inside the project folder and served by Django itself
in production too, which works but is slower under load than letting Apache
serve them directly.

If you want Apache to serve `/media/` directly instead (recommended once
traffic grows):

1. Point `DJANGO_MEDIA_ROOT` at a folder Apache can reach, e.g.
   `/home/cpaneluser/urbanpantry/media`.
2. In cPanel's Domain/subdomain settings (or an `.htaccess` in
   `public_html`), add an alias so requests to `/media/...` are served
   directly from that folder instead of hitting Passenger.

Either way, make sure the folder is writable by the app
(`chmod 755` on the folder is usually enough; cPanel's Python App runs as
your own user, so this is rarely an issue).

## 7. Restart the app

In **Setup Python App**, click **Restart**. Any time you deploy new code,
change env vars, or run new migrations, restart again so Passenger picks up
the change (it caches the running process).

## Local development is unaffected

Nothing here requires local changes: `DJANGO_DEBUG` defaults to `True` and
`DB_ENGINE` is unset by default, so `python manage.py runserver` locally
still uses SQLite with debug mode on, exactly as before.
