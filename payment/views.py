from decimal import Decimal, ROUND_DOWN
from uuid import UUID
from django.db import transaction
from paycomuz import Paycom
from paycomuz.views import MerchantAPIView
from payment.models import Order
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from core.settings import SITE_URL
from payment.utils import update_user_payment


class CheckOrder(Paycom):
    def check_order(self, amount, account, *args, **kwargs):
        """Buyurtmani tekshirish"""
        try:
            order_id = UUID(account["order_id"])
        except ValueError:
            return self.ORDER_NOT_FOND

        order = Order.objects.filter(id=order_id, is_finished=False).first()
        if not order:
            return self.ORDER_NOT_FOND
        if order.total * 100 != amount:
            return self.INVALID_AMOUNT
        return self.ORDER_FOUND

    @transaction.atomic
    def successfully_payment(self, account, transaction, *args, **kwargs):
        """To‘lov muvaffaqiyatli amalga oshganda ishlaydi"""
        try:
            order_id = UUID(transaction.order_key)
        except ValueError:
            return self.ORDER_NOT_FOUND

        order = Order.objects.filter(id=order_id, is_finished=False).first()
        if not order:
            return self.ORDER_NOT_FOUND

        order.is_finished = True
        order.save()

        update_user_payment(order.user_id, order.total)

    def cancel_payment(self, account, transaction, *args, **kwargs):
        """To‘lov bekor qilinganda ishlaydi"""
        print(f"Transaction canceled: {transaction.order_key}")


class TestView(MerchantAPIView):
    """Paycom test API"""
    VALIDATE_CLASS = CheckOrder

    @extend_schema(
        summary="Paycom bilan bog‘liq test API",
        description="Bu API Paycom orqali to‘lovni tekshirish va boshqarish uchun ishlatiladi.",
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class PaycomInitializationView(APIView):
    """Paycom orqali to‘lovni boshlash"""

    @extend_schema(
        summary="Paycom orqali to‘lovni boshlash",
        description="Foydalanuvchiga Paycom orqali to‘lov qilish uchun URL qaytaradi.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "example": 12345},
                    "amount": {"type": "number", "example": 45000}
                },
                "required": ["user_id", "amount"],
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "payment_url": {"type": "string", "example": "https://checkout.paycom.uz/..."}
                },
            },
            400: {"description": "Xato: user_id yoki amount noto‘g‘ri"},
        },
    )
    def post(self, request):
        user_id = request.data.get("user_id")
        amount = request.data.get("amount")

        if not isinstance(user_id, int) or not isinstance(amount, (int, float, str)):
            return Response({"error": "user_id butun son bo‘lishi kerak va amount raqam bo‘lishi kerak"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            order = Order.objects.create(user_id=user_id, total=int(amount))
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        except Exception:
            return Response({"error": "Noto‘g‘ri amount qiymati"}, status=status.HTTP_400_BAD_REQUEST)

        paycom = Paycom()
        url = paycom.create_initialization(
            amount=amount,
            order_id=str(order.id),
            return_url=f"http://{SITE_URL}/api/paycom/",
        )

        return Response({"payment_url": url, "order_id": str(order.id)}, status=status.HTTP_200_OK)
