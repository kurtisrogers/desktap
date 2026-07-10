from django.conf import settings
from django.core import signing

VIEWPORT_COOKIE_NAME = "desktap_viewport"
VIEWPORT_SALT = "desktap.viewport.v1"


def sign_viewport_width(width: int) -> str:
    return signing.dumps({"width": width}, salt=VIEWPORT_SALT)


def get_viewport_width(request) -> int | None:
    raw = request.COOKIES.get(VIEWPORT_COOKIE_NAME)
    if not raw:
        return None
    try:
        data = signing.loads(raw, salt=VIEWPORT_SALT, max_age=60 * 60 * 24)
    except signing.BadSignature:
        return None
    width = data.get("width")
    if isinstance(width, int):
        return width
    return None


def viewport_too_small(request) -> bool:
    width = get_viewport_width(request)
    if width is None:
        return False
    return width < settings.MIN_VIEWPORT_WIDTH
