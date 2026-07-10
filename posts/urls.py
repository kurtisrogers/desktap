from django.urls import path

from . import views

app_name = "posts"

urlpatterns = [
    path("feed/", views.feed, name="feed"),
    path("feed/post/", views.create_post, name="create_post"),
    path("post/<int:pk>/", views.post_detail, name="post_detail"),
    path("post/<int:pk>/comment/", views.add_comment, name="add_comment"),
    path("post/<int:pk>/like/", views.toggle_like, name="toggle_like"),
    path("post/<int:pk>/delete/", views.delete_own_post, name="delete_post"),
    path("comment/<int:pk>/delete/", views.delete_own_comment, name="delete_comment"),
    path("profile/<str:username>/", views.profile, name="profile"),
    path("profile/<str:username>/follow/", views.toggle_follow, name="toggle_follow"),
    path(
        "report/<str:content_type>/<int:content_id>/",
        views.report_content,
        name="report_content",
    ),
]
