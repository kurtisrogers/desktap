from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.forms import ReportForm
from accounts.models import User
from moderation.models import AuditLog, ContentReport
from moderation.utils import log_action

from .forms import CommentForm, PostForm
from .models import Comment, Follow, Post


def _visible_posts():
    return Post.objects.filter(is_hidden=False).select_related("author")


@login_required
def feed(request):
    following_ids = Follow.objects.filter(follower=request.user).values_list(
        "following_id",
        flat=True,
    )
    author_filter = Q(author=request.user) | Q(author_id__in=following_ids)
    posts = _visible_posts().filter(author_filter)[:50]
    post_form = PostForm()
    return render(
        request,
        "posts/feed.html",
        {"posts": posts, "post_form": post_form},
    )


@login_required
@require_POST
def create_post(request):
    form = PostForm(request.POST)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
    return redirect("posts:feed")


@login_required
def post_detail(request, pk):
    post = get_object_or_404(_visible_posts(), pk=pk)
    comments = post.comments.filter(is_hidden=False).select_related("author")
    comment_form = CommentForm()
    report_form = ReportForm()
    return render(
        request,
        "posts/post_detail.html",
        {
            "post": post,
            "comments": comments,
            "comment_form": comment_form,
            "report_form": report_form,
        },
    )


@login_required
@require_POST
def add_comment(request, pk):
    post = get_object_or_404(_visible_posts(), pk=pk)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
    return redirect("posts:post_detail", pk=pk)


@login_required
@require_POST
def toggle_like(request, pk):
    post = get_object_or_404(_visible_posts(), pk=pk)
    if request.user in post.likes.all():
        post.likes.remove(request.user)
    else:
        post.likes.add(request.user)
    if request.headers.get("HX-Request"):
        return render(request, "posts/partials/like_button.html", {"post": post})
    return redirect("posts:post_detail", pk=pk)


@login_required
def profile(request, username):
    profile_user = get_object_or_404(User, username=username, is_suspended=False)
    posts = profile_user.posts.filter(is_hidden=False)[:30]
    is_following = Follow.objects.filter(
        follower=request.user,
        following=profile_user,
    ).exists()
    can_follow = profile_user != request.user
    return render(
        request,
        "posts/profile.html",
        {
            "profile_user": profile_user,
            "posts": posts,
            "is_following": is_following,
            "can_follow": can_follow,
        },
    )


@login_required
@require_POST
def toggle_follow(request, username):
    profile_user = get_object_or_404(User, username=username)
    if profile_user == request.user:
        return redirect("posts:profile", username=username)
    follow, created = Follow.objects.get_or_create(
        follower=request.user,
        following=profile_user,
    )
    if not created:
        follow.delete()
    return redirect("posts:profile", username=username)


@login_required
@require_POST
def report_content(request, content_type, content_id):
    form = ReportForm(request.POST)
    if not form.is_valid():
        return redirect("posts:feed")
    if content_type not in ("post", "comment"):
        return redirect("posts:feed")
    ContentReport.objects.create(
        reporter=request.user,
        content_type=content_type,
        content_id=content_id,
        reason=form.cleaned_data["reason"],
        details=form.cleaned_data.get("details", ""),
    )
    return redirect(request.META.get("HTTP_REFERER", "posts:feed"))


@login_required
@require_POST
def delete_own_post(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user)
    post.delete()
    return redirect("posts:feed")


@login_required
@require_POST
def delete_own_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk, author=request.user)
    post_pk = comment.post_id
    comment.delete()
    return redirect("posts:post_detail", pk=post_pk)
