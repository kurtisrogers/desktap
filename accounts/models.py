from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class UserRole(models.TextChoices):
    ADULT = "adult", "Adult"
    CHILD = "child", "Child"
    SUPPORT = "support", "Support"
    SUPERADMIN = "superadmin", "Superadmin"


class User(AbstractUser):
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=100, blank=True)
    bio = models.CharField(max_length=500, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.ADULT,
    )
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    card_verified = models.BooleanField(default=False)
    is_parent = models.BooleanField(default=False)
    parent_account = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children_accounts",
    )
    is_suspended = models.BooleanField(default=False)
    totp_enrolled = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    REQUIRED_FIELDS = ["email"]

    def save(self, *args, **kwargs):
        if not self.display_name:
            self.display_name = self.username
        super().save(*args, **kwargs)

    @property
    def is_staff_role(self) -> bool:
        return self.role in (UserRole.SUPPORT, UserRole.SUPERADMIN)

    @property
    def is_superadmin(self) -> bool:
        return self.role == UserRole.SUPERADMIN

    @property
    def is_child(self) -> bool:
        return self.role == UserRole.CHILD

    @property
    def requires_card_verification(self) -> bool:
        return self.role in (UserRole.ADULT,) and not self.is_child

    @property
    def onboarding_complete(self) -> bool:
        if self.is_suspended:
            return False
        if self.is_child:
            return self.totp_enrolled
        if self.role == UserRole.ADULT:
            return self.card_verified and self.totp_enrolled
        if self.is_staff_role:
            return self.totp_enrolled
        return self.totp_enrolled

    def __str__(self) -> str:
        return self.username


class ParentChildLink(models.Model):
    parent = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="child_links",
    )
    child = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="parent_link",
    )
    child_disabled = models.BooleanField(default=False)
    linked_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["parent", "child"],
                name="unique_parent_child",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.parent.username} -> {self.child.username}"


class ChildInvite(models.Model):
    parent = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="child_invites",
    )
    email = models.EmailField()
    username = models.CharField(max_length=150)
    date_of_birth = models.DateField()
    token = models.CharField(max_length=64, unique=True)
    accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"Invite {self.username} ({self.email})"
