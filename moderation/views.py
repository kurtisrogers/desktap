from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User, UserRole
from posts.models import Comment, Post

from .models import ContentReport, ReportStatus
from .utils import log_action


def staff_required(view_func):
    def wrapper(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated or user.role not in (
            UserRole.SUPPORT,
            UserRole.SUPERADMIN,
        ):
            return HttpResponseForbidden()
        return view_func(request, *args, **kwargs)

    return wrapper


@login_required
@staff_required
def report_queue(request):
    reports = ContentReport.objects.filter(status=ReportStatus.OPEN).select_related(
        "reporter"
    )
    enriched = []
    for report in reports:
        content = None
        if report.content_type == "post":
            content = Post.objects.filter(pk=report.content_id).first()
        elif report.content_type == "comment":
            content = Comment.objects.filter(pk=report.content_id).select_related(
                "post"
            ).first()
        enriched.append({"report": report, "content": content})
    return render(request, "moderation/report_queue.html", {"reports": enriched})


@login_required
@staff_required
@require_POST
def hide_content(request, report_id):
    report = get_object_or_404(ContentReport, pk=report_id)
    if report.content_type == "post":
        Post.objects.filter(pk=report.content_id).update(is_hidden=True)
    elif report.content_type == "comment":
        Comment.objects.filter(pk=report.content_id).update(is_hidden=True)
    report.status = ReportStatus.RESOLVED
    report.handled_by = request.user
    report.save()
    log_action(
        request.user,
        "hide_content",
        report.content_type,
        report.content_id,
        {"report_id": report_id},
    )
    return redirect("moderation:report_queue")


@login_required
@staff_required
@require_POST
def suspend_user(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if target.role == UserRole.SUPERADMIN:
        return HttpResponseForbidden()
    if (
        target.role == UserRole.SUPPORT
        and request.user.role != UserRole.SUPERADMIN
    ):
        return HttpResponseForbidden()
    target.is_suspended = True
    target.save(update_fields=["is_suspended"])
    log_action(request.user, "suspend_user", "user", target.pk)
    return redirect("moderation:report_queue")


@login_required
@staff_required
@require_POST
def dismiss_report(request, report_id):
    report = get_object_or_404(ContentReport, pk=report_id)
    report.status = ReportStatus.DISMISSED
    report.handled_by = request.user
    report.save()
    log_action(
        request.user,
        "dismiss_report",
        "report",
        report.pk,
    )
    return redirect("moderation:report_queue")
