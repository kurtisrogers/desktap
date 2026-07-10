import secrets

import stripe
from django.conf import settings


def stripe_configured() -> bool:
    return bool(settings.STRIPE_SECRET_KEY) and not settings.STRIPE_DEV_MODE


def create_setup_intent(user) -> dict:
    if not stripe_configured():
        return {"client_secret": "dev_mode", "dev_mode": True}

    stripe.api_key = settings.STRIPE_SECRET_KEY
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            name=user.display_name or user.username,
            metadata={"user_id": str(user.pk)},
        )
        user.stripe_customer_id = customer.id
        user.save(update_fields=["stripe_customer_id"])

    intent = stripe.SetupIntent.create(
        customer=user.stripe_customer_id,
        payment_method_types=["card"],
        usage="off_session",
        metadata={"user_id": str(user.pk)},
    )
    return {"client_secret": intent.client_secret, "dev_mode": False}


def handle_setup_intent_succeeded(event_data: dict) -> int | None:
    metadata = event_data.get("metadata", {})
    user_id = metadata.get("user_id")
    if user_id:
        return int(user_id)
    return None
