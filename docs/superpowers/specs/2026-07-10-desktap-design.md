# Desktap — Design Specification

**Date:** 2026-07-10  
**Status:** Draft — pending user review  
**Stack:** Django 5.x, PostgreSQL, Tailwind CSS, HTMX, Stripe

---

## 1. Product Overview

**Desktap** is a desktop-only social network that encourages mindful screen use and online safety. Users get profiles, a chronological feed, and comments. The platform is intentionally inaccessible on mobile devices.

### Core Principles

1. **No mobile** — Hard block via user-agent detection and minimum viewport width (1024px).
2. **Genuine users** — Every adult account requires credit card verification (no charge) via Stripe.
3. **Safety by design** — Parental oversight for minors; mandatory two-factor authentication (2FA) for all users.
4. **Staff governance** — Superadmin and Support roles for site management and moderation.

### v1 Feature Scope

| In scope | Out of scope (later) |
|----------|----------------------|
| Profiles | Direct messaging |
| Feed (chronological) | Groups / communities |
| Comments | Stories / reels |
| Follow users | Notifications (email only for v1 invites) |
| Likes | Media uploads (text-only v1) |
| Parent dashboard | Real-time updates (WebSockets) |
| Staff moderation queue | Mobile apps |
| Card verification | Paid subscriptions |

---

## 2. User Roles & Permissions

Five account types enforced via a custom Django User model and permission groups.

| Role | Who | Capabilities |
|------|-----|------------|
| **Superadmin** | Site owners | Full access: users, posts, comments, bans, settings, promote/demote staff, view audit logs |
| **Support** | Moderators / help desk | View users & content, hide/delete posts & comments, suspend accounts, respond to reports — **cannot** change site settings or manage other staff |
| **Adult** | 18+, card-verified, 2FA-enrolled | Profile, feed, post, comment, follow |
| **Parent** | Adult + `is_parent` flag | Everything Adult has, plus: create/link child accounts, parent dashboard, disable child account |
| **Child** | Under 18, linked to verified parent, 2FA-enrolled | Profile, feed, post, comment — cannot exist without active parent link |

### Staff vs Users

- Superadmin and Support are **staff roles** (`is_staff=True`), assigned manually by Superadmin (not self-signup).
- First Superadmin: created via Django `createsuperuser` at deploy time.
- Support accounts: created by Superadmin in admin or staff-only UI.

### Permission Matrix (v1)

| Action | Superadmin | Support | Parent | Adult | Child |
|--------|:----------:|:-------:|:------:|:-----:|:-----:|
| Post / comment | ✓ | ✓ | ✓ | ✓ | ✓ |
| View any user's content | ✓ | ✓ | Own children only | Own only | Own only |
| Delete any post/comment | ✓ | ✓ | — | Own only | Own only |
| Suspend/disable account | ✓ | ✓ | Own children only | — | — |
| Manage staff roles | ✓ | — | — | — | — |
| Site settings | ✓ | — | — | — | — |

---

## 3. Two-Factor Authentication (2FA)

**2FA is a hard requirement for all users** — Adult, Parent, Child, Support, and Superadmin. No user can access any authenticated page without a verified 2FA device enrolled.

### Method

- **TOTP** (Time-based One-Time Password) via authenticator apps (Google Authenticator, Authy, 1Password, etc.).
- Implemented with `django-otp` (TOTP devices).

### Enforcement Rules

1. **Signup flow gate** — After card verification (adults) or password setup (children), user must enroll 2FA before accessing feed or any authenticated feature.
2. **Login flow** — Username/password → TOTP challenge → session created. No "skip for now" option.
3. **Staff accounts** — Same requirement; Superadmin must enroll 2FA on first login.
4. **Recovery** — Backup codes generated at enrollment (10 single-use codes). Lost device → contact Support with identity verification (manual process in v1).
5. **Session** — Re-prompt for TOTP after 30 days of inactivity or on new browser/device (configurable via `OTP_TOTP_ISSUER` and session settings).

### User Experience

- Enrollment page: QR code + manual secret key + backup codes download.
- Login page: password field → redirect to TOTP entry (not on same form, to prevent credential stuffing).
- Middleware: `OTPMiddleware` + custom check that redirects unenrolled authenticated users to enrollment.

---

## 4. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Desktap (Django)                     │
├──────────────┬──────────────┬──────────────┬─────────────┤
│   accounts   │    posts     │  moderation  │    core     │
│  (auth,      │  (feed,      │  (reports,   │  (mobile    │
│   roles,     │   profiles,  │   staff      │   block     │
│   stripe,    │   comments)  │   actions)   │   middleware)│
│   2FA,       │              │              │             │
│   parent/    │              │              │             │
│   child)     │              │              │             │
├──────────────┴──────────────┴──────────────┴─────────────┤
│  PostgreSQL          │  Stripe (card verify)              │
└─────────────────────────────────────────────────────────┘
```

### Django Apps

| App | Responsibility |
|-----|----------------|
| `core` | Mobile-block middleware, base templates, site-wide settings, desktop-only landing page |
| `accounts` | Custom User model, signup, Stripe verification, 2FA enrollment/login, parent/child linking, parent dashboard |
| `posts` | Profiles, feed, posts, comments, follows, likes |
| `moderation` | Content reports, staff queue, audit log |

### Tech Stack

| Layer | Choice |
|-------|--------|
| Framework | Django 5.x |
| Database | PostgreSQL |
| CSS | Tailwind CSS (desktop-first, min-width layouts) |
| Interactivity | HTMX (inline comments, likes, feed pagination) |
| 2FA | django-otp (TOTP) |
| Payments | Stripe SetupIntent (card verification, no charge) |
| Static files | WhiteNoise |
| Production server | Gunicorn + Nginx |

Redis is optional in v1; add later for caching or session storage if needed.

---

## 5. Mobile Block

Implemented in `core` middleware, evaluated on every request.

### Layer 1: User-Agent Check

- Block known mobile and tablet user-agent strings.
- Allow desktop browsers only.

### Layer 2: Viewport Check

- JavaScript on first visit sets a session cookie with `screen.width`.
- Middleware rejects requests where viewport width < 1024px.
- Prevents resizing a desktop browser window below threshold as a workaround (cookie checked server-side).

### Fallback Page

Friendly "Desktap is desktop-only" page explaining:
- Why the platform exists (mindful screen use, safety).
- Encouragement to step away from the phone.
- No app store links, no "continue anyway" bypass.

---

## 6. Data Model

### User

```
User (extends AbstractUser)
├── email (unique)
├── username (unique)
├── display_name
├── bio (max 500 chars)
├── avatar (optional, v1 may use initials placeholder)
├── date_of_birth
├── role: adult | child | support | superadmin
├── stripe_customer_id
├── card_verified (bool)
├── is_parent (bool)
├── parent → User (FK, nullable — set for children)
├── is_suspended (bool)
├── totp_enrolled (bool) — denormalized for middleware fast-path
└── created_at
```

### ParentChildLink

```
ParentChildLink
├── parent → User
├── child → User (unique)
├── child_disabled (bool)
└── linked_at
```

### Post

```
Post
├── author → User
├── content (text, max 2000 chars)
├── created_at
├── is_hidden (bool, moderation)
└── likes → User (M2M)
```

### Comment

```
Comment
├── post → Post
├── author → User
├── content (text, max 500 chars)
├── created_at
├── is_hidden (bool)
└── parent_comment → Comment (nullable, reserved for threading in v2)
```

### Follow

```
Follow
├── follower → User
├── following → User
├── unique_together (follower, following)
└── created_at
```

### ContentReport

```
ContentReport
├── reporter → User
├── content_type: post | comment
├── content_id (PositiveIntegerField)
├── reason (choices + optional free text)
├── status: open | resolved | dismissed
├── handled_by → User (nullable, staff)
└── created_at
```

### AuditLog

```
AuditLog
├── actor → User (staff)
├── action (e.g. hide_post, suspend_user, dismiss_report)
├── target_type, target_id
├── metadata (JSONField, optional context)
└── timestamp
```

### TOTPDevice (django-otp)

Managed by `django-otp`; linked to User. Backup codes stored as `StaticDevice` tokens.

---

## 7. Key User Flows

### Adult Signup

1. Register: email, username, password, date of birth (must be 18+).
2. Stripe card verification (SetupIntent, no charge).
3. Enroll 2FA (QR code, backup codes).
4. Profile setup → feed.

User cannot proceed past step 2 without completing step 3.

### Child Signup (via Parent)

1. Parent (card-verified, 2FA-enrolled) navigates to "Add child".
2. Enters child's email, username, date of birth (must be under 18).
3. Child receives invite email → sets password.
4. Child enrolls 2FA (QR code, backup codes).
5. Account active, linked to parent → feed.

Child does not require separate card verification; parent's account satisfies the family trust chain.

### Login (all users)

1. Enter username/email + password.
2. Redirect to TOTP challenge.
3. On success → session created → feed.

### Parent Dashboard

- List linked children with active/disabled status.
- Per child: read-only list of posts and comments (paginated).
- Toggle to disable/enable child account (`ParentChildLink.child_disabled`).
- Disabled child: cannot log in; sees "Account disabled by parent" message.

### Staff Moderation

1. Support/Superadmin views open `ContentReport` queue.
2. Actions: hide content, suspend user, dismiss report.
3. All actions logged in `AuditLog`.

### Card Verification (Stripe)

- Use Stripe **SetupIntent** with `payment_method_options.card.request_three_d_secure: automatic`.
- On `setup_intent.succeeded` webhook → set `user.card_verified = True`.
- No charge, no subscription. Purpose: confirm card is real (reduces fake accounts).
- Store `stripe_customer_id` on User for potential future use; no payment history in v1.

---

## 8. URL Structure (v1)

| Path | Description |
|------|-------------|
| `/` | Landing page (public, desktop-only) |
| `/signup/` | Adult registration |
| `/login/` | Login + 2FA challenge |
| `/verify-card/` | Stripe card verification step |
| `/enroll-2fa/` | 2FA enrollment (post-signup gate) |
| `/feed/` | Main feed |
| `/profile/<username>/` | User profile |
| `/post/<id>/` | Single post with comments |
| `/parent/` | Parent dashboard |
| `/parent/add-child/` | Create child account |
| `/settings/` | Profile settings, 2FA management |
| `/staff/reports/` | Moderation queue (staff only) |
| `/admin/` | Django admin (superadmin) |
| `/blocked/` | Mobile-blocked fallback page |

---

## 9. Security Considerations

| Concern | Mitigation |
|---------|------------|
| Fake accounts | Card verification + mandatory 2FA |
| Underage without oversight | Child accounts require linked parent; parent can disable |
| Mobile bypass | UA + viewport dual check |
| Session hijacking | Secure cookies, HTTPS only, TOTP re-challenge on new device |
| Staff abuse | Audit log on all moderation actions; Support cannot manage staff |
| CSRF | Django CSRF middleware on all forms |
| XSS | Django template auto-escaping |
| Child safety | Text-only v1 (no image uploads); content reports; parent read-only monitoring |

---

## 10. Testing Strategy (v1)

| Area | Approach |
|------|----------|
| Mobile block middleware | Unit tests: UA strings, viewport cookie values |
| 2FA enforcement | Integration tests: unenrolled user redirected; login requires TOTP |
| Parent/child linking | Tests: child cannot sign up without parent; disabled child cannot log in |
| Card verification | Mock Stripe webhooks in tests |
| Permissions | Tests per role for each protected view |
| Feed/posts | Basic CRUD and visibility tests |

---

## 11. Deployment (outline)

- Environment variables: `SECRET_KEY`, `DATABASE_URL`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `OTP_TOTP_ISSUER=Desktap`
- `python manage.py migrate` + `createsuperuser` for first Superadmin
- Stripe webhook endpoint registered for `setup_intent.succeeded`
- HTTPS required in production (secure cookies, Stripe requirement)

---

## 12. Open Decisions (resolved)

| Question | Decision |
|----------|----------|
| Tech stack | Django monolith, templates + HTMX |
| v1 features | Profiles, feed, comments only |
| Mobile block | Hard: UA + 1024px viewport |
| Card verification | All adults; Stripe SetupIntent, no charge |
| Children | Linked to parent; no own card |
| Parent oversight | Read-only monitoring + disable account |
| Staff roles | Superadmin + Support |
| 2FA | Mandatory TOTP for all users via django-otp |

---

## 13. Future (post-v1)

- Direct messaging
- Groups / communities
- Image uploads with moderation
- Email notifications for activity
- Real-time feed (Django Channels)
- Native desktop app (Electron/Tauri) — aligns with desktop-only mission
