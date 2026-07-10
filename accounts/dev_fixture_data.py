"""Shared constants and helpers for local development fixtures."""

from __future__ import annotations

import base64
from datetime import date

from django_otp.oath import totp
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from accounts.models import User, UserRole

# Known credentials for every seeded account.
DEV_PASSWORD = "devpass123"

# Standard RFC 6238 test secret ("Hello!") — use in any authenticator app.
DEV_TOTP_SECRET_BASE32 = "JBSWY3DPEHPK3PXP"
DEV_TOTP_HEX_KEY = base64.b32decode(DEV_TOTP_SECRET_BASE32, casefold=True).hex()

DEV_BACKUP_CODES = tuple(f"backup-{index:02d}" for index in range(1, 6))

SEED_USERNAMES = (
    "superadmin",
    "support",
    "alex",
    "riley",
    "jamie_parent",
    "sam_child",
)


def current_totp_code() -> str:
    return str(totp(bytes.fromhex(DEV_TOTP_HEX_KEY))).zfill(6)


def enroll_totp(user: User) -> TOTPDevice:
    TOTPDevice.objects.filter(user=user).delete()
    device = TOTPDevice.objects.create(
        user=user,
        name="default",
        confirmed=True,
        key=DEV_TOTP_HEX_KEY,
    )
    user.totp_enrolled = True
    user.save(update_fields=["totp_enrolled"])
    return device


def enroll_backup_codes(user: User) -> list[str]:
    device, _ = StaticDevice.objects.get_or_create(user=user, name="backup")
    device.token_set.all().delete()
    codes = []
    for code in DEV_BACKUP_CODES:
        StaticToken.objects.create(device=device, token=code)
        codes.append(code)
    return codes


def create_verified_adult(
    *,
    username: str,
    email: str,
    display_name: str,
    bio: str = "",
    date_of_birth: date | None = None,
    is_parent: bool = False,
) -> User:
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": email,
            "display_name": display_name,
            "bio": bio,
            "date_of_birth": date_of_birth or date(1990, 1, 15),
            "role": UserRole.ADULT,
            "card_verified": True,
            "is_parent": is_parent,
        },
    )
    if created:
        user.set_password(DEV_PASSWORD)
        user.save()
    else:
        user.email = email
        user.display_name = display_name
        user.bio = bio
        user.role = UserRole.ADULT
        user.card_verified = True
        user.is_parent = is_parent
        user.is_suspended = False
        user.set_password(DEV_PASSWORD)
        user.save()

    enroll_totp(user)
    enroll_backup_codes(user)
    return user


def credential_summary() -> str:
    code = current_totp_code()
    lines = [
        "",
        "Dev login credentials",
        "=====================",
        f"Password (all accounts): {DEV_PASSWORD}",
        f"TOTP secret (base32):    {DEV_TOTP_SECRET_BASE32}",
        f"Current TOTP code:       {code}",
        f"Backup codes:            {', '.join(DEV_BACKUP_CODES)}",
        "",
        "Accounts:",
    ]
    for username in SEED_USERNAMES:
        lines.append(f"  - {username}")
    lines.extend(
        [
            "",
            "Log in from a desktop browser (1024px+ wide), then enter the TOTP code.",
            "Codes rotate every 30 seconds; re-run seed_dev to print a fresh code.",
            "",
        ]
    )
    return "\n".join(lines)
