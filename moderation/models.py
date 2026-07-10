from django.db import models
from django.utils import timezone

from accounts.models import User


class ReportStatus(models.TextChoices):
    OPEN = "open", "Open"
    RESOLVED = "resolved", "Resolved"
    DISMISSED = "dismissed", "Dismissed"


class ContentType(models.TextChoices):
    POST = "post", "Post"
    COMMENT = "comment", "Comment"


class ContentReport(models.Model):
    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reports_filed",
    )
    content_type = models.CharField(max_length=20, choices=ContentType.choices)
    content_id = models.PositiveIntegerField()
    reason = models.CharField(max_length=50)
    details = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.OPEN,
    )
    handled_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reports_handled",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Report {self.content_type}:{self.content_id} ({self.status})"


class AuditLog(models.Model):
    actor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="audit_actions",
    )
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=50)
    target_id = models.PositiveIntegerField()
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"{self.actor.username} {self.action} {self.target_type}:{self.target_id}"
