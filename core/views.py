from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from core.viewport import sign_viewport_width


def landing(request):
    return render(request, "core/landing.html")


def blocked(request):
    return render(request, "core/blocked.html")


@require_POST
def set_viewport(request):
    try:
        width = int(request.POST.get("width", 0))
    except (TypeError, ValueError):
        return JsonResponse({"error": "invalid width"}, status=400)

    response = JsonResponse({"ok": True, "width": width})
    response.set_cookie(
        "desktap_viewport",
        sign_viewport_width(width),
        max_age=60 * 60 * 24,
        httponly=True,
        samesite="Lax",
    )
    return response
