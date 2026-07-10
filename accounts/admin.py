from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import ChildInvite, ParentChildLink, SecurityEvent, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "role",
        "card_verified",
        "totp_enrolled",
        "is_parent",
        "is_suspended",
    )
    list_filter = ("role", "card_verified", "totp_enrolled", "is_suspended", "is_parent")
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Desktap",
            {
                "fields": (
                    "display_name",
                    "bio",
                    "date_of_birth",
                    "role",
                    "stripe_customer_id",
                    "card_verified",
                    "is_parent",
                    "parent_account",
                    "is_suspended",
                    "totp_enrolled",
                ),
            },
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "Desktap",
            {
                "fields": ("email", "role"),
            },
        ),
    )


@admin.register(ParentChildLink)
class ParentChildLinkAdmin(admin.ModelAdmin):
    list_display = ("parent", "child", "child_disabled", "linked_at")
    list_filter = ("child_disabled",)


@admin.register(ChildInvite)
class ChildInviteAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "parent", "accepted", "created_at")
    list_filter = ("accepted",)


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "user", "ip_address", "created_at")
    list_filter = ("event_type",)
    readonly_fields = ("event_type", "user", "ip_address", "user_agent", "metadata", "created_at")
