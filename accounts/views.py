import base64
import io
import secrets

import qrcode
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django_otp import devices_for_user, match_token
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from .forms import (
    AddChildForm,
    ChildSetupForm,
    LoginForm,
    ProfileSettingsForm,
    SignupForm,
    TotpVerifyForm,
)
from .models import ChildInvite, ParentChildLink, User, UserRole
from .security import (
    clear_rate_limit,
    get_client_ip,
    is_rate_limited,
    log_security_event,
    login_rate_limit_settings,
    record_rate_limit_attempt,
)
from .stripe_utils import (
    create_setup_intent,
    handle_setup_intent_succeeded,
    stripe_configured,
    verify_setup_intent,
)


def _generate_backup_codes(user, count=10) -> list[str]:
    device, _ = StaticDevice.objects.get_or_create(
        user=user,
        name="backup",
    )
    device.token_set.all().delete()
    codes = []
    for _ in range(count):
        token = StaticToken.random_token()
        StaticToken.objects.create(device=device, token=token)
        codes.append(token)
    return codes


def _get_or_create_totp_device(user) -> TOTPDevice:
    device = TOTPDevice.objects.filter(user=user, confirmed=False).first()
    if device is None:
        device = TOTPDevice.objects.create(user=user, name="default", confirmed=False)
    return device


def _qr_data_url(config_url: str) -> str:
    img = qrcode.make(config_url)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def signup(request):
    if request.user.is_authenticated:
        return redirect("posts:feed")
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("accounts:verify_card")
    else:
        form = SignupForm()
    return render(request, "accounts/signup.html", {"form": form})


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("posts:feed")

    limit, period = login_rate_limit_settings()
    ip = get_client_ip(request)
    lock_key = f"{ip}"

    if request.method == "POST":
        if is_rate_limited("login", lock_key, limit, period):
            log_security_event("login_locked", request=request, metadata={"ip": ip})
            form = LoginForm(request, data=request.POST)
            form.add_error(None, "Too many login attempts. Please try again later.")
            return render(request, "accounts/login.html", {"form": form})

        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            clear_rate_limit("login", lock_key)
            request.session["pre_2fa_user_id"] = user.pk
            return redirect("accounts:verify_2fa_login")

        record_rate_limit_attempt("login", lock_key, period)
        log_security_event(
            "login_failed",
            request=request,
            metadata={"username": request.POST.get("username", "")},
        )
    else:
        form = LoginForm(request)
    return render(request, "accounts/login.html", {"form": form})


@require_http_methods(["GET", "POST"])
def verify_2fa_login(request):
    user_id = request.session.get("pre_2fa_user_id")
    if not user_id:
        return redirect("accounts:login")
    user = get_object_or_404(User, pk=user_id)

    if request.method == "POST":
        form = TotpVerifyForm(request.POST)
        if form.is_valid():
            token = form.cleaned_data["token"].replace(" ", "")
            if match_token(user, token):
                del request.session["pre_2fa_user_id"]
                login(request, user)
                request.session["otp_verified"] = True
                log_security_event("login_success", request=request, user=user)
                if not user.onboarding_complete:
                    if not user.card_verified and user.role == UserRole.ADULT:
                        return redirect("accounts:verify_card")
                    if not user.totp_enrolled:
                        return redirect("accounts:enroll_2fa")
                return redirect("posts:feed")
            form.add_error("token", "Invalid authentication code.")
            log_security_event("totp_failed", request=request, user=user)
    else:
        form = TotpVerifyForm()
    return render(request, "accounts/verify_2fa_login.html", {"form": form})


@login_required
def verify_card(request):
    user = request.user
    if user.card_verified:
        return redirect("accounts:enroll_2fa" if not user.totp_enrolled else "posts:feed")

    intent_data = create_setup_intent(user)
    if intent_data.get("setup_intent_id"):
        request.session["pending_setup_intent_id"] = intent_data["setup_intent_id"]
    context = {
        "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        "client_secret": intent_data["client_secret"],
        "dev_mode": intent_data.get("dev_mode", False),
    }
    return render(request, "accounts/verify_card.html", context)


@login_required
@require_POST
def verify_card_dev(request):
    if not settings.STRIPE_DEV_MODE:
        return HttpResponseForbidden()
    user = request.user
    user.card_verified = True
    user.save(update_fields=["card_verified"])
    log_security_event("card_verified", request=request, user=user)
    return redirect("accounts:enroll_2fa")


@login_required
def enroll_2fa(request):
    user = request.user
    backup_codes = request.session.pop("backup_codes", None)

    if user.totp_enrolled and backup_codes is None:
        return redirect("posts:feed")

    device = _get_or_create_totp_device(user)

    if request.method == "POST":
        form = TotpVerifyForm(request.POST)
        if form.is_valid():
            token = form.cleaned_data["token"].replace(" ", "")
            if device.verify_token(token):
                device.confirmed = True
                device.save()
                user.totp_enrolled = True
                user.save(update_fields=["totp_enrolled"])
                backup_codes = _generate_backup_codes(user)
                request.session["backup_codes"] = backup_codes
                return redirect("accounts:enroll_2fa")
            form.add_error("token", "Invalid code. Scan the QR code and try again.")
    else:
        form = TotpVerifyForm()

    config_url = device.config_url
    context = {
        "form": form,
        "qr_data_url": _qr_data_url(config_url),
        "config_url": config_url,
        "backup_codes": backup_codes,
        "enrollment_complete": user.totp_enrolled and backup_codes is not None,
    }
    return render(request, "accounts/enroll_2fa.html", context)


@login_required
def settings_view(request):
    if request.method == "POST":
        form = ProfileSettingsForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("accounts:settings")
    else:
        form = ProfileSettingsForm(instance=request.user)
    devices = list(devices_for_user(request.user))
    return render(
        request,
        "accounts/settings.html",
        {"form": form, "devices": devices},
    )


@login_required
def parent_dashboard(request):
    user = request.user
    if not user.is_parent and user.role != UserRole.ADULT:
        return HttpResponseForbidden()
    links = ParentChildLink.objects.filter(parent=user).select_related("child")
    return render(request, "accounts/parent_dashboard.html", {"links": links})


@login_required
def parent_child_detail(request, child_id):
    user = request.user
    link = get_object_or_404(ParentChildLink, parent=user, child_id=child_id)
    child = link.child
    posts = child.posts.filter(is_hidden=False).order_by("-created_at")[:50]
    comments = (
        child.comments.filter(is_hidden=False).select_related("post").order_by("-created_at")[:50]
    )
    return render(
        request,
        "accounts/parent_child_detail.html",
        {"link": link, "child": child, "posts": posts, "comments": comments},
    )


@login_required
@require_POST
def parent_toggle_child(request, child_id):
    link = get_object_or_404(ParentChildLink, parent=request.user, child_id=child_id)
    link.child_disabled = not link.child_disabled
    link.save(update_fields=["child_disabled"])
    log_security_event(
        "child_disabled",
        request=request,
        user=request.user,
        metadata={"child_id": link.child_id, "disabled": link.child_disabled},
    )
    return redirect("accounts:parent_dashboard")


@login_required
def add_child(request):
    user = request.user
    if not user.card_verified or not user.totp_enrolled:
        return redirect("posts:feed")

    if request.method == "POST":
        form = AddChildForm(request.POST)
        if form.is_valid():
            invite = form.save(commit=False)
            invite.parent = user
            invite.token = secrets.token_urlsafe(32)
            invite.save()
            user.is_parent = True
            user.save(update_fields=["is_parent"])
            setup_url = request.build_absolute_uri(
                reverse("accounts:child_setup", kwargs={"token": invite.token})
            )
            from django.core.mail import send_mail

            send_mail(
                subject="Your Desktap account invite",
                message=f"Set up your Desktap account: {setup_url}",
                from_email=None,
                recipient_list=[invite.email],
            )
            return render(
                request,
                "accounts/add_child_done.html",
                {"invite": invite, "setup_url": setup_url},
            )
    else:
        form = AddChildForm()
    return render(request, "accounts/add_child.html", {"form": form})


@require_http_methods(["GET", "POST"])
def child_setup(request, token):
    invite = get_object_or_404(ChildInvite, token=token, accepted=False)
    if request.method == "POST":
        form = ChildSetupForm(request.POST)
        if form.is_valid():
            child = User.objects.create_user(
                username=invite.username,
                email=invite.email,
                password=form.cleaned_data["password1"],
                date_of_birth=invite.date_of_birth,
                role=UserRole.CHILD,
                parent_account=invite.parent,
                card_verified=True,
            )
            ParentChildLink.objects.create(parent=invite.parent, child=child)
            invite.accepted = True
            invite.save(update_fields=["accepted"])
            login(request, child)
            return redirect("accounts:enroll_2fa")
    else:
        form = ChildSetupForm()
    return render(
        request,
        "accounts/child_setup.html",
        {"form": form, "invite": invite},
    )


@csrf_exempt
@require_POST
def stripe_webhook(request):

    import stripe as stripe_lib

    if not stripe_configured():
        return JsonResponse({"status": "ignored"})

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    try:
        event = stripe_lib.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except (ValueError, stripe_lib.error.SignatureVerificationError):
        return JsonResponse({"error": "invalid"}, status=400)

    if event["type"] == "setup_intent.succeeded":
        user_id = handle_setup_intent_succeeded(event["data"]["object"])
        if user_id:
            User.objects.filter(pk=user_id).update(card_verified=True)
            log_security_event(
                "card_verified",
                metadata={"user_id": user_id, "source": "stripe_webhook"},
            )
    return JsonResponse({"status": "ok"})


@login_required
@require_POST
def card_verified_complete(request):
    user = request.user
    setup_intent_id = request.session.get("pending_setup_intent_id")

    if settings.STRIPE_DEV_MODE:
        user.card_verified = True
        user.save(update_fields=["card_verified"])
        log_security_event("card_verified", request=request, user=user)
        return redirect("accounts:enroll_2fa")

    if setup_intent_id and verify_setup_intent(setup_intent_id):
        user.card_verified = True
        user.save(update_fields=["card_verified"])
        del request.session["pending_setup_intent_id"]
        log_security_event("card_verified", request=request, user=user)
        return redirect("accounts:enroll_2fa")

    return HttpResponseForbidden("Card verification has not been confirmed.")


def suspended(request):
    return render(request, "accounts/suspended.html")
