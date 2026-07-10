# Desktap MVP Implementation Plan

> **Goal:** Build v1 of Desktap — a Django desktop-only social network with card verification, mandatory 2FA, and parent/child safety features.

**Architecture:** Django monolith with server-rendered templates, HTMX for likes, django-otp for TOTP 2FA, Stripe SetupIntent for card verification.

**Tech Stack:** Django 5.x, SQLite/PostgreSQL, Tailwind-inspired CSS, HTMX, django-otp, Stripe, WhiteNoise

---

## Status: MVP scaffold complete

Implemented in this branch:
- Django project with `core`, `accounts`, `posts`, `moderation` apps
- Custom User model with roles (adult, child, support, superadmin)
- Mobile block middleware (user-agent + viewport cookie)
- Adult signup, Stripe card verify (dev mode fallback), mandatory 2FA enrollment
- Login with TOTP challenge
- Parent dashboard, child invites, disable child accounts
- Feed, posts, comments, likes, follows, profiles
- Content reports and staff moderation queue
- 8 passing tests
