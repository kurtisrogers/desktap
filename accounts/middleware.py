ONBOARDING_EXEMPT_PREFIXES = (
    "/accounts/login",
    "/accounts/logout",
    "/accounts/signup",
    "/accounts/verify-card",
    "/accounts/enroll-2fa",
    "/accounts/child-setup",
    "/accounts/stripe-webhook",
    "/static/",
    "/blocked/",
    "/admin/login",
)


class OnboardingGateMiddleware:
    """Redirect users who have not finished card verify + 2FA enrollment."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        path = request.path

        if user.is_authenticated and not any(
            path.startswith(prefix) for prefix in ONBOARDING_EXEMPT_PREFIXES
        ):
            if user.is_suspended:
                pass
            elif (
                user.is_child
                and hasattr(user, "parent_link")
                and user.parent_link.child_disabled
            ):
                from django.contrib.auth import logout
                from django.contrib import messages
                from django.shortcuts import redirect

                messages.error(request, "Your account has been disabled by your parent.")
                logout(request)
                return redirect("accounts:login")
            elif not user.totp_enrolled:
                from django.shortcuts import redirect

                return redirect("accounts:enroll_2fa")
            elif user.role == "adult" and not user.card_verified:
                from django.shortcuts import redirect

                return redirect("accounts:verify_card")

        return self.get_response(request)
