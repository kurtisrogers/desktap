from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import ParentChildLink, UserRole
from core.middleware import is_mobile_user_agent

User = get_user_model()


class MobileBlockTests(TestCase):
    def test_detects_iphone_user_agent(self):
        self.assertTrue(is_mobile_user_agent("Mozilla/5.0 (iPhone; CPU iPhone OS 14_0)"))

    def test_allows_desktop_user_agent(self):
        self.assertFalse(
            is_mobile_user_agent(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
            )
        )

    def test_blocks_mobile_on_landing(self):
        client = Client(HTTP_USER_AGENT="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0)")
        response = client.get(reverse("core:landing"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("core:blocked"))

    def test_allows_desktop_with_viewport_cookie(self):
        client = Client(
            HTTP_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        )
        client.cookies["desktap_viewport_width"] = "1920"
        response = client.get(reverse("core:landing"))
        self.assertEqual(response.status_code, 200)


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
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "adultuser",
                "email": "adult@example.com",
                "date_of_birth": dob.isoformat(),
                "password1": "complexpass123",
                "password2": "complexpass123",
            },
            HTTP_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        )
        self.client.cookies["desktap_viewport_width"] = "1920"
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="adultuser")
        self.assertEqual(user.role, UserRole.ADULT)


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
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "child1", "password": "complexpass123"},
            HTTP_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        )
        self.client.cookies["desktap_viewport_width"] = "1920"
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "disabled")


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
        self.client.login(username="poster", password="complexpass123")
        response = self.client.post(
            reverse("posts:create_post"),
            {"content": "Hello Desktap!"},
            HTTP_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        )
        self.client.cookies["desktap_viewport_width"] = "1920"
        self.assertEqual(response.status_code, 302)
        from posts.models import Post

        self.assertEqual(Post.objects.count(), 1)
