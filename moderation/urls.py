from django.urls import path

from . import views

app_name = "moderation"

urlpatterns = [
    path("reports/", views.report_queue, name="report_queue"),
    path("reports/<int:report_id>/hide/", views.hide_content, name="hide_content"),
    path(
        "reports/<int:report_id>/dismiss/",
        views.dismiss_report,
        name="dismiss_report",
    ),
    path("users/<int:user_id>/suspend/", views.suspend_user, name="suspend_user"),
]
