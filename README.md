<div align="center">

# Desktap

**Social networking for desktop. Step away from your phone.**

A Django social network that is intentionally unavailable on mobile — built for mindful screen use and online safety.

[![CI](https://github.com/kurtisrogers/desktap/actions/workflows/ci.yml/badge.svg)](https://github.com/kurtisrogers/desktap/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12+-blue)
![Django](https://img.shields.io/badge/django-5.x-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

[Features](#features) · [Safety](#safety--security) · [Quick start](#quick-start) · [Testing](#testing) · [Design spec](docs/superpowers/specs/2026-07-10-desktap-design.md)

</div>

---

## Why Desktap?

Most social networks are designed for phones — infinite scroll, push notifications, always-on engagement. Desktap flips that:

- **Desktop only** — blocked on phones and tablets (user-agent + signed viewport check)
- **Verified humans** — credit card verification (no charge) + mandatory 2FA for every user
- **Family safety** — children join only through a verified parent who can monitor and disable accounts
- **Staff moderation** — Superadmin and Support roles with audit logging

## Features

| Feature | Description |
|---------|-------------|
| Feed & profiles | Chronological feed, posts, comments, likes, follows |
| Desktop gate | Hard block below 1024px; friendly “put your phone down” page |
| Card verify | Stripe SetupIntent — confirms identity, never charges |
| 2FA | TOTP required for all users; backup codes on enrollment |
| Parent dashboard | Read-only child activity view + disable toggle |
| Moderation | Content reports, staff queue, suspend users, audit trail |

## Safety & security

- **Login rate limiting** — lockout after repeated failed attempts
- **Content safety** — blocks phone numbers, emails, external links, and harmful phrases in posts/comments
- **Security events** — audit log for logins, 2FA failures, card verification, suspensions
- **Signed viewport cookies** — tamper-resistant desktop verification
- **Security headers** — CSP, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`
- **Production hardening** — HSTS, secure cookies, SSL redirect when `DEBUG=False`

## Quick start

```bash
git clone https://github.com/kurtisrogers/desktap.git
cd desktap
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_dev
python manage.py runserver
```

Open **http://127.0.0.1:8000** from a desktop browser (1024px+ wide).

### Signup flow

1. Register (18+)
2. Verify card (`STRIPE_DEV_MODE=True` simulates this in dev)
3. Enroll 2FA (scan QR code)
4. Post to your feed

### Dev fixtures

Load ready-made accounts, posts, follows, and a sample moderation report:

```bash
python manage.py seed_dev          # load fixtures
python manage.py seed_dev --flush  # reset seeded data first
```

| Username | Role | Notes |
|----------|------|-------|
| `superadmin` | Superadmin | Full admin access |
| `support` | Support | Moderation queue |
| `alex` | Adult | Posts and follows |
| `riley` | Adult | Posts and follows |
| `jamie_parent` | Parent | Linked to `sam_child` |
| `sam_child` | Child | Parent dashboard testing |

All seeded accounts share:

- **Password:** `devpass123`
- **TOTP secret:** `JBSWY3DPEHPK3PXP` (add to any authenticator app)
- **Backup codes:** `backup-01` … `backup-05`

The command prints the current 6-digit TOTP code when it finishes.

### Dev tips

- Child invite links print to the console (email backend is console)
- Install pre-commit hooks: `pre-commit install`

## Testing

```bash
# Unit tests (Django)
python manage.py test

# BDD tests (pytest-bdd)
pytest tests/bdd -v

# Lint
ruff check .

# Pre-commit (all hooks)
pre-commit run --all-files
```

## Project structure

```
desktap/          # Django settings & URLs
accounts/         # Auth, 2FA, Stripe, parent/child, security events
core/             # Mobile block, viewport signing, landing page
posts/            # Feed, profiles, social interactions
moderation/       # Reports, staff queue, audit log
tests/bdd/        # BDD feature files (Gherkin)
```

## Environment variables

See [`.env.example`](.env.example).

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Django secret key |
| `STRIPE_*` | Card verification (optional in dev) |
| `STRIPE_DEV_MODE` | Simulate card verify without Stripe |
| `OTP_TOTP_ISSUER` | Label shown in authenticator apps |

## Contributing

1. Fork the repo
2. Create a branch: `git checkout -b skynet/my-feature-e1ba`
3. Install pre-commit: `pre-commit install`
4. Run tests before pushing
5. Open a pull request

## License

MIT — use freely, modify responsibly.
