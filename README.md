# Desktap

A desktop-only social network built with Django. Encourages mindful screen use and online safety.

## Features

- **Desktop only** — blocked on mobile user-agents and viewports under 1024px
- **Profiles, feed, comments, follows, likes**
- **Card verification** (Stripe SetupIntent, no charge) for all adult accounts
- **Mandatory 2FA** (TOTP) for every user
- **Parent/child accounts** — children join via parent invite; parents can monitor and disable
- **Staff roles** — Superadmin and Support with moderation queue

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit http://127.0.0.1:8000 from a desktop browser.

### Development notes

- `STRIPE_DEV_MODE=True` in `.env` simulates card verification without Stripe keys.
- Email is printed to the console (child invite links appear in terminal).
- After `createsuperuser`, set `role=superadmin` and complete 2FA enrollment on first login.

## Environment variables

See `.env.example`.

## Tests

```bash
python manage.py test
```

## Design spec

See `docs/superpowers/specs/2026-07-10-desktap-design.md`.
