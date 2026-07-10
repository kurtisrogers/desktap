from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserRole
from accounts.tests import desktop_client
from moderation.models import AuditLog, ContentReport, ReportStatus
from posts.models import Post

User = get_user_model()


class ModerationTests(TestCase):
    def setUp(self):
        self.support = User.objects.create_user(
            username="support1",
            email="support@example.com",
            password="complexpass123",
            role=UserRole.SUPPORT,
            card_verified=True,
            totp_enrolled=True,
            is_staff=True,
        )
        self.author = User.objects.create_user(
            username="badactor",
            email="bad@example.com",
            password="complexpass123",
            card_verified=True,
            totp_enrolled=True,
        )
        self.post = Post.objects.create(author=self.author, content="Bad post")
        self.report = ContentReport.objects.create(
            reporter=self.author,
            content_type="post",
            content_id=self.post.pk,
            reason="harassment",
        )

    def test_support_can_view_queue(self):
        client = desktop_client()
        client.force_login(self.support)
        response = client.get(reverse("moderation:report_queue"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Report")

    def test_hide_content_resolves_report(self):
        client = desktop_client()
        client.force_login(self.support)
        client.post(reverse("moderation:hide_content", kwargs={"report_id": self.report.pk}))
        self.post.refresh_from_db()
        self.report.refresh_from_db()
        self.assertTrue(self.post.is_hidden)
        self.assertEqual(self.report.status, ReportStatus.RESOLVED)
        self.assertTrue(AuditLog.objects.filter(action="hide_content").exists())

    def test_suspend_user(self):
        client = desktop_client()
        client.force_login(self.support)
        client.post(reverse("moderation:suspend_user", kwargs={"user_id": self.author.pk}))
        self.author.refresh_from_db()
        self.assertTrue(self.author.is_suspended)
