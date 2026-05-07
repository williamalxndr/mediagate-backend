from __future__ import annotations

from apps.core.models import Order


class OrderNotFoundError(Exception):
    pass


class OrderAlreadyFulfilledError(Exception):
    pass


class OrderNotFulfilledError(Exception):
    pass


def list_orders(status: str | None = None):
    qs = Order.objects.select_related(
        "access_token",
        "access_token__content",
        "access_token__content__event",
    ).all()
    if status:
        qs = qs.filter(status=status)
    return qs


def get_order_by_id(pk: int) -> Order:
    try:
        return Order.objects.select_related(
            "access_token",
            "access_token__content",
            "access_token__content__event",
        ).get(pk=pk)
    except Order.DoesNotExist:
        raise OrderNotFoundError("Order not found.")
