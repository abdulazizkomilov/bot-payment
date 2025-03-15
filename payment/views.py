from uuid import UUID
from django.db import transaction
from paycomuz import Paycom
from paycomuz.views import MerchantAPIView
from payment.models import Order
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema


class CheckOrder(Paycom):
    def check_order(self, amount, account, *args, **kwargs):
        try:
            order_id = UUID(account["order_id"])  # UUID validatsiyasi
        except ValueError:
            return self.ORDER_NOT_FOND  # Yaroqsiz UUID bo‘lsa, xatolik

        order = Order.objects.filter(id=order_id, is_finished=False).first()
        if not order:
            return self.ORDER_NOT_FOND
        if order.total * 100 != amount:
            return self.INVALID_AMOUNT
        return self.ORDER_FOUND

    @transaction.atomic  # Ma'lumotlar bazasida o'zgarishlarni xavfsiz qilish
    def successfully_payment(self, account, transaction, *args, **kwargs):
        try:
            order_id = UUID(transaction.order_key)
        except ValueError:
            return self.ORDER_NOT_FOUND  # Yaroqsiz UUID bo‘lsa, xatolik

        order = Order.objects.filter(id=order_id).first()
        if not order:
            return self.ORDER_NOT_FOUND

        order.is_finished = True
        order.save()

    def cancel_payment(self, account, transaction, *args, **kwargs):
        print("Transaction canceled:", transaction.order_key)


class TestView(MerchantAPIView):
    VALIDATE_CLASS = CheckOrder

    @extend_schema(
        summary="Paycom bilan bog‘liq test API",
        description="Bu API Paycom orqali to‘lovni tekshirish va boshqarish uchun ishlatiladi.",
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class PaycomInitializationView(APIView):
    @extend_schema(
        summary="Paycom orqali to‘lovni boshlash",
        description="Foydalanuvchiga Paycom orqali to‘lov qilish uchun URL qaytaradi.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "example": "4148e2a8-443b-4c09-803e-e51694004acc"},
                    "amount": {"type": "number", "example": 10000.00}
                },
                "required": ["order_id", "amount"],
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "payment_url": {"type": "string", "example": "https://checkout.paycom.uz/..."}
                },
            },
            400: {"description": "Xato: order_id yoki amount noto‘g‘ri"},
            404: {"description": "Buyurtma topilmadi"},
        },
    )
    def post(self, request):
        order_id = request.data.get("order_id")
        amount = request.data.get("amount")

        if not order_id or not amount:
            return Response({"error": "order_id va amount talab qilinadi"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = Order.objects.get(id=order_id, is_finished=False)
        except Order.DoesNotExist:
            return Response({"error": "Buyurtma topilmadi yoki allaqachon tugatilgan"},
                            status=status.HTTP_404_NOT_FOUND)

        paycom = Paycom()
        url = paycom.create_initialization(
            amount=float(amount),
            order_id=str(order.id),
            return_url="https://863e-188-113-234-128.ngrok-free.app/paycom/success",
        )

        return Response({"payment_url": url}, status=status.HTTP_200_OK)
