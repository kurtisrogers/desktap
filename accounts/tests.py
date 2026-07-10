from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.models import ParentChildLink, SecurityEvent, UserRole
from core.middleware import is_mobile_user_agent
from core.viewport import get_viewport_width, sign_viewport_width

User = get_user_model()
DESKTOP_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"


def desktop_client() -> Client:
    client = Client(HTTP_USER_AGENT=DESKTOP_UA)
    client.cookies["desktap_viewport"] = sign_viewport_width(1920)
    return client


class MobileBlockTests(TestCase):
    def test_detects_iphone_user_agent(self):
        self.assertTrue(is_mobile_user_agent("Mozilla/5.0 (iPhone; CPU iPhone OS 14_0)"))

    def test_allows_desktop_user_agent(self):
        self.assertFalse(is_mobile_user_agent(DESKTOP_UA))

    def test_blocks_mobile_on_landing(self):
        client = Client(HTTP_USER_AGENT="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0)")
        response = client.get(reverse("core:landing"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("core:blocked"))

    def test_allows_desktop_with_signed_viewport_cookie(self):
        client = desktop_client()
        response = client.get(reverse("core:landing"))
        self.assertEqual(response.status_code, 200)

    def test_rejects_tampered_viewport_cookie(self):
        from django.test import RequestFactory

        request = RequestFactory().get("/")
        request.COOKIES["desktap_viewport"] = "forged-value"
        self.assertIsNone(get_viewport_width(request))


class SignupTests(TestCase):
    def test_adult_signup_requires_18(self):
        young_dob = date.today() - timedelta(days=365 * 17)
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "younguser",
                "email": "young@example.com",
                "date_of_birth": young_dob.isoformat(),
                "password1": "complexpass123",
                "password2": "complexpass123",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="younguser").exists())

    def test_adult_signup_success(self):
        dob = date.today() - timedelta(days=365 * 25)
        client = desktop_client()
        response = client.post(
            reverse("accounts:signup"),
            {
                "username": "adultuser",
                "email": "adult@example.com",
                "date_of_birth": dob.isoformat(),
                "password1": "complexpass123",
                "password2": "complexpass123",
            },
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="adultuser")
        self.assertEqual(user.role, UserRole.ADULT)


class LoginSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="loginuser",
            email="login@example.com",
            password="complexpass123",
            card_verified=True,
            totp_enrolled=True,
        )

    def test_failed_login_creates_security_event(self):
        client = desktop_client()
        client.post(
            reverse("accounts:login"),
            {"username": "loginuser", "password": "wrong"},
        )
        self.assertTrue(SecurityEvent.objects.filter(event_type="login_failed").exists())

    def test_rate_limit_locks_login(self):
        client = desktop_client()
        for _ in range(6):
            client.post(
                reverse("accounts:login"),
                {"username": "loginuser", "password": "wrong"},
            )
        response = client.post(
            reverse("accounts:login"),
            {"username": "loginuser", "password": "wrong"},
        )
        self.assertContains(response, "Too many login attempts")


class ParentChildTests(TestCase):
    def setUp(self):
        self.parent = User.objects.create_user(
            username="parent1",
            email="parent@example.com",
            password="complexpass123",
            role=UserRole.ADULT,
            card_verified=True,
            totp_enrolled=True,
            is_parent=True,
        )
        self.child = User.objects.create_user(
            username="child1",
            email="child@example.com",
            password="complexpass123",
            role=UserRole.CHILD,
            parent_account=self.parent,
            totp_enrolled=True,
        )
        ParentChildLink.objects.create(
            parent=self.parent,
            child=self.child,
        )

    def test_disabled_child_cannot_login(self):
        link = ParentChildLink.objects.get(child=self.child)
        link.child_disabled = True
        link.save()
        client = desktop_client()
        response = client.post(
            reverse("accounts:login"),
            {"username": "child1", "password": "complexpass123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "disabled")

    def test_suspended_user_is_logged_out(self):
        self.parent.is_suspended = True
        self.parent.save()
        client = desktop_client()
        client.force_login(self.parent)
        response = client.get(reverse("posts:feed"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("accounts:suspended"))


class PostTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="poster",
            email="poster@example.com",
            password="complexpass123",
            card_verified=True,
            totp_enrolled=True,
        )

    def test_create_post(self):
        client = desktop_client()
        client.force_login(self.user)
        response = client.post(
            reverse("posts:create_post"),
            {"content": "Hello Desktap!"},
        )
        self.assertEqual(response.status_code, 302)
        from posts.models import Post

        self.assertEqual(Post.objects.count(), 1)

    def test_blocks_phone_number_in_post(self):
        client = desktop_client()
        client.force_login(self.user)
        response = client.post(
            reverse("posts:create_post"),
            {"content": "Call me at 555-123-4567"},
        )
        self.assertEqual(response.status_code, 302)
        from posts.models import Post

        self.assertEqual(Post.objects.count(), 0)


class SeedDevCommandTests(TestCase):
    @override_settings(DEBUG=True)
    def test_seed_dev_creates_expected_users(self):
        from django.core.management import call_command

        from accounts.dev_fixture_data import SEED_USERNAMES

        call_command("seed_dev", verbosity=0)
        self.assertEqual(User.objects.filter(username__in=SEED_USERNAMES).count(), 6)

    @override_settings(DEBUG=True)
    def test_seed_dev_users_can_authenticate(self):
        from django.core.management import call_command

        from accounts.dev_fixture_data import DEV_PASSWORD

        call_command("seed_dev", verbosity=0)
        user = User.objects.get(username="alex")
        self.assertTrue(user.check_password(DEV_PASSWORD))
        self.assertTrue(user.totp_enrolled)
        self.assertTrue(user.card_verified)

    @override_settings(DEBUG=True)
    def test_seed_dev_creates_social_content(self):
        from django.core.management import call_command

        from posts.models import Comment, Follow, Post

        call_command("seed_dev", verbosity=0)
        self.assertGreaterEqual(Post.objects.count(), 4)
        self.assertGreaterEqual(Comment.objects.count(), 2)
        self.assertGreaterEqual(Follow.objects.count(), 3)

    @override_settings(DEBUG=True)
    def test_seed_dev_creates_parent_child_link(self):
        from django.core.management import call_command

        call_command("seed_dev", verbosity=0)
        self.assertTrue(
            ParentChildLink.objects.filter(
                parent__username="jamie_parent",
                child__username="sam_child",
            ).exists()
        )

    @override_settings(DEBUG=True)
    def test_seed_dev_creates_open_report(self):
        from django.core.management import call_command

        from moderation.models import ContentReport

        call_command("seed_dev", verbosity=0)
        self.assertTrue(ContentReport.objects.filter(status="open").exists())

    @override_settings(DEBUG=True)
    def test_current_totp_code_is_six_digits(self):
        from django.core.management import call_command

        from accounts.dev_fixture_data import current_totp_code

        call_command("seed_dev", verbosity=0)
        code = current_totp_code()
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

    @override_settings(DEBUG=False)
    def test_seed_dev_refuses_when_debug_disabled(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command("seed_dev", verbosity=0)
