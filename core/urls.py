from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("blocked/", views.blocked, name="blocked"),
    path("set-viewport/", views.set_viewport, name="set_viewport"),
]
