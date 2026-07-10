from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("verify-2fa/", views.verify_2fa_login, name="verify_2fa_login"),
    path("verify-card/", views.verify_card, name="verify_card"),
    path("verify-card/dev/", views.verify_card_dev, name="verify_card_dev"),
    path("verify-card/complete/", views.card_verified_complete, name="card_verified_complete"),
    path("enroll-2fa/", views.enroll_2fa, name="enroll_2fa"),
    path("settings/", views.settings_view, name="settings"),
    path("parent/", views.parent_dashboard, name="parent_dashboard"),
    path("parent/add-child/", views.add_child, name="add_child"),
    path(
        "parent/child/<int:child_id>/",
        views.parent_child_detail,
        name="parent_child_detail",
    ),
    path(
        "parent/child/<int:child_id>/toggle/",
        views.parent_toggle_child,
        name="parent_toggle_child",
    ),
    path("child-setup/<str:token>/", views.child_setup, name="child_setup"),
    path("stripe-webhook/", views.stripe_webhook, name="stripe_webhook"),
]
