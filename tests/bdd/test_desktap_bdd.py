import pytest
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.django_db

scenarios("mobile_block.feature")
scenarios("content_safety.feature")


@given("I am using a desktop browser", target_fixture="client")
def desktop_browser():
    from accounts.tests import desktop_client

    return desktop_client()


@given("I am using a mobile browser", target_fixture="client")
def mobile_browser():
    from django.test import Client

    return Client(HTTP_USER_AGENT="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)")


@when("I visit the landing page", target_fixture="response")
def visit_landing(client):
    from django.urls import reverse

    return client.get(reverse("core:landing"))


@then("I should see the landing page")
def see_landing(response):
    assert response.status_code == 200
    assert b"Social networking, without the phone" in response.content


@then("I should be redirected to the blocked page")
def redirected_blocked(response):
    from django.urls import reverse

    assert response.status_code == 302
    assert response.url == reverse("core:blocked")


@given("a verified user is logged in", target_fixture="client")
def verified_user():
    from django.contrib.auth import get_user_model

    from accounts.tests import desktop_client

    client = desktop_client()
    User = get_user_model()
    user = User.objects.create_user(
        username="bdduser",
        email="bdd@example.com",
        password="complexpass123",
        card_verified=True,
        totp_enrolled=True,
    )
    client.force_login(user)
    return client


@when(parsers.parse('I try to post "{content}"'))
def try_post(client, content):
    from django.urls import reverse

    client.post(reverse("posts:create_post"), {"content": content})


@then("the post should be rejected")
def post_rejected():
    from posts.models import Post

    assert Post.objects.count() == 0


@then("the post should be accepted")
def post_accepted():
    from posts.models import Post

    assert Post.objects.count() == 1
