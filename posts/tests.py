from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.tests import desktop_client
from posts.models import Follow, Post

User = get_user_model()


class FeedTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            username="author",
            email="author@example.com",
            password="complexpass123",
            card_verified=True,
            totp_enrolled=True,
        )
        self.viewer = User.objects.create_user(
            username="viewer",
            email="viewer@example.com",
            password="complexpass123",
            card_verified=True,
            totp_enrolled=True,
        )
        Post.objects.create(author=self.author, content="Author post")
        Post.objects.create(author=self.viewer, content="Viewer post")

    def test_feed_shows_own_posts(self):
        client = desktop_client()
        client.force_login(self.viewer)
        response = client.get(reverse("posts:feed"))
        self.assertContains(response, "Viewer post")

    def test_feed_shows_followed_posts(self):
        Follow.objects.create(follower=self.viewer, following=self.author)
        client = desktop_client()
        client.force_login(self.viewer)
        response = client.get(reverse("posts:feed"))
        self.assertContains(response, "Author post")


class ProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="profileuser",
            email="profile@example.com",
            password="complexpass123",
            card_verified=True,
            totp_enrolled=True,
            display_name="Profile User",
        )

    def test_profile_page(self):
        client = desktop_client()
        client.force_login(self.user)
        response = client.get(reverse("posts:profile", kwargs={"username": "profileuser"}))
        self.assertContains(response, "Profile User")
