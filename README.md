# Backend

Django + Django REST Framework service for token validation, access control, and signed URL generation.

## Structure

- `config`: Django project config, URLs, ASGI/WSGI, and settings.
- `apps.core`: Central database models, migrations, and model admin registrations.
- `apps.core.roles`: Admin role helpers backed by the Django `admin` group.
- `common.permissions`: Shared DRF permissions, including Admin API access.
- `apps.events`, `apps.content`, `apps.access`: Domain API, selectors, services, and tests.
- `common`: Shared backend helpers.

## Local Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py check
```
