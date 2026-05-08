from __future__ import annotations

import re
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.access.services import create_access_token, revoke_access_token
from apps.core.models import Order

from .selectors import OrderAlreadyFulfilledError, OrderNotFulfilledError

DEFAULT_TOKEN_LIFETIME = timedelta(days=7)
DEFAULT_MAX_DURATION_SECONDS = 24 * 3600


class InvalidWhatsAppNumberError(Exception):
    pass


def normalize_whatsapp(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if not digits:
        raise InvalidWhatsAppNumberError("WhatsApp number is required.")
    if digits.startswith("0"):
        digits = "62" + digits[1:]
    if len(digits) < 8:
        raise InvalidWhatsAppNumberError("WhatsApp number is too short.")
    return digits


def create_order(
    *,
    customer_name: str,
    whatsapp_number: str,
    content_id: int,
) -> Order:
    e164 = normalize_whatsapp(whatsapp_number)
    return Order.objects.create(
        customer_name=customer_name.strip(),
        whatsapp_number=whatsapp_number.strip(),
        whatsapp_e164=e164,
        content_id=content_id,
    )


class OrderMissingContentError(Exception):
    pass


@transaction.atomic
def issue_token_for_order(order: Order) -> Order:
    if order.status == Order.STATUS_FULFILLED:
        raise OrderAlreadyFulfilledError("Order already has a token issued.")
    if order.status == Order.STATUS_CANCELLED:
        raise OrderAlreadyFulfilledError("Order is cancelled.")
    if not order.content_id:
        raise OrderMissingContentError("Order has no content; cannot issue a token.")
    token = create_access_token(
        content_id=order.content_id,
        expires_at=timezone.now() + DEFAULT_TOKEN_LIFETIME,
        max_duration=DEFAULT_MAX_DURATION_SECONDS,
    )
    order.access_token = token
    order.status = Order.STATUS_FULFILLED
    order.save(update_fields=["access_token", "status", "updated_at"])
    return order


@transaction.atomic
def regenerate_token_for_order(order: Order) -> Order:
    if order.status != Order.STATUS_FULFILLED or not order.access_token_id:
        raise OrderNotFulfilledError("Order has no token to regenerate.")
    if not order.content_id:
        raise OrderMissingContentError("Order has no content; cannot regenerate token.")
    revoke_access_token(order.access_token)
    new_token = create_access_token(
        content_id=order.content_id,
        expires_at=timezone.now() + DEFAULT_TOKEN_LIFETIME,
        max_duration=DEFAULT_MAX_DURATION_SECONDS,
    )
    order.access_token = new_token
    order.save(update_fields=["access_token", "updated_at"])
    return order


def cancel_order(order: Order) -> Order:
    if order.status == Order.STATUS_FULFILLED:
        raise OrderAlreadyFulfilledError("Cannot cancel a fulfilled order.")
    order.status = Order.STATUS_CANCELLED
    order.save(update_fields=["status", "updated_at"])
    return order
