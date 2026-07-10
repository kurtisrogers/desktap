import re

from core.viewport import viewport_too_small

MOBILE_UA_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"android",
        r"iphone",
        r"ipod",
        r"ipad",
        r"windows phone",
        r"blackberry",
        r"mobile",
        r"webos",
        r"opera mini",
        r"opera mobi",
        r"silk/",
        r"kindle",
    )
]

EXEMPT_PATH_PREFIXES = (
    "/static/",
    "/blocked/",
    "/set-viewport/",
)


def is_mobile_user_agent(user_agent: str) -> bool:
    if not user_agent:
        return False
    return any(pattern.search(user_agent) for pattern in MOBILE_UA_PATTERNS)


class MobileBlockMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if any(path.startswith(prefix) for prefix in EXEMPT_PATH_PREFIXES):
            return self.get_response(request)

        user_agent = request.META.get("HTTP_USER_AGENT", "")
        if is_mobile_user_agent(user_agent) or viewport_too_small(request):
            from django.shortcuts import redirect

            if path != "/blocked/":
                return redirect("core:blocked")
        return self.get_response(request)
