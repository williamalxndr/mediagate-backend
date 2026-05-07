from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from common.permissions import IsAdminApiUser

from ..selectors import (
    OrderAlreadyFulfilledError,
    OrderNotFoundError,
    OrderNotFulfilledError,
    get_order_by_id,
    list_orders,
)
from ..services import (
    OrderMissingContentError,
    cancel_order,
    create_order,
    issue_token_for_order,
    regenerate_token_for_order,
)
from .serializers import (
    OrderAdminListSerializer,
    OrderCreateSerializer,
    OrderPublicCreateResponseSerializer,
)


class OrderCreateView(APIView):
    """POST /api/orders/ — anonymous, create a pending order."""

    authentication_classes = []
    permission_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "orders_public"

    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = create_order(**serializer.validated_data)
        return Response(
            OrderPublicCreateResponseSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )


class OrderAdminListView(APIView):
    """GET /api/orders/admin/ — list orders, optional ?status= filter."""

    permission_classes = [IsAdminApiUser]

    def get(self, request):
        status_filter = request.query_params.get("status") or None
        orders = list_orders(status=status_filter)
        return Response(
            {"results": OrderAdminListSerializer(orders, many=True).data}
        )


class OrderAdminDetailView(APIView):
    """GET /api/orders/admin/<pk>/ — fetch a single order."""

    permission_classes = [IsAdminApiUser]

    def get(self, request, pk):
        try:
            order = get_order_by_id(pk)
        except OrderNotFoundError:
            return Response(
                {"detail": "Order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(OrderAdminListSerializer(order).data)


class OrderIssueTokenView(APIView):
    """POST /api/orders/admin/<pk>/issue-token/ — create token + fulfill."""

    permission_classes = [IsAdminApiUser]

    def post(self, request, pk):
        try:
            order = get_order_by_id(pk)
        except OrderNotFoundError:
            return Response(
                {"detail": "Order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            order = issue_token_for_order(order)
        except OrderAlreadyFulfilledError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )
        except OrderMissingContentError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            OrderAdminListSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )


class OrderRegenerateTokenView(APIView):
    """POST /api/orders/admin/<pk>/regenerate-token/ — revoke + reissue."""

    permission_classes = [IsAdminApiUser]

    def post(self, request, pk):
        try:
            order = get_order_by_id(pk)
        except OrderNotFoundError:
            return Response(
                {"detail": "Order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            order = regenerate_token_for_order(order)
        except (OrderNotFulfilledError, OrderMissingContentError) as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            OrderAdminListSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )


class OrderCancelView(APIView):
    """PATCH /api/orders/admin/<pk>/cancel/ — cancel a pending order."""

    permission_classes = [IsAdminApiUser]

    def patch(self, request, pk):
        try:
            order = get_order_by_id(pk)
        except OrderNotFoundError:
            return Response(
                {"detail": "Order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            order = cancel_order(order)
        except OrderAlreadyFulfilledError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(OrderAdminListSerializer(order).data)
