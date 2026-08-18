"""
Order Views - Card-to-Card Payment Flow (ADR-005 + D-067)
"""
import logging
from decimal import Decimal

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.conf import settings

from .models import Cart, CartItem, Order, OrderItem, Payment, Address
from .services import get_or_create_cart, add_to_cart, update_cart_item, remove_from_cart
from .serializers import CartSerializer, OrderSerializer, AddressSerializer, PaymentSerializer
from .payment_gateway import get_payment_gateway, CardToCardGateway

logger = logging.getLogger(__name__)


class CartViewSet(viewsets.ViewSet):
    """
    API سبد خرید (بدون تغییر - همان منطق قبلی)
    - GET  /cart/             : مشاهده سبد
    - POST /cart/add/         : افزودن کالا
    - PUT  /cart/update_item/ : به‌روزرسانی تعداد
    - DEL  /cart/remove/      : حذف کالا
    """
    
    def list(self, request):
        cart = get_or_create_cart(request)
        serializer = CartSerializer(cart)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def add(self, request):
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        
        if not product_id:
            return Response({'error': 'product_id الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cart = get_or_create_cart(request)
            add_to_cart(cart, product_id, quantity)
            serializer = CartSerializer(cart)
            return Response({
                'message': 'کالا با موفقیت به سبد اضافه شد',
                'cart': serializer.data
            }, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['put'])
    def update_item(self, request):
        item_id = request.data.get('item_id')
        quantity = request.data.get('quantity')
        
        if not item_id or quantity is None:
            return Response({'error': 'item_id و quantity الزامی هستند'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cart = get_or_create_cart(request)
            update_cart_item(cart, item_id, int(quantity))
            serializer = CartSerializer(cart)
            return Response({'message': 'سبد به‌روزرسانی شد', 'cart': serializer.data})
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['delete'])
    def remove(self, request):
        item_id = request.data.get('item_id')
        if not item_id:
            return Response({'error': 'item_id الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cart = get_or_create_cart(request)
            remove_from_cart(cart, item_id)
            serializer = CartSerializer(cart)
            return Response({'message': 'کالا حذف شد', 'cart': serializer.data})
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def checkout(self, request):
        """
        نهایی‌سازی سفارش از سبد خرید
        سفارش در وضعیت DRAFT ایجاد می‌شود و منتظر پرداخت می‌ماند
        """
        cart = get_or_create_cart(request)
        
        if not cart.items.exists():
            return Response({'error': 'سبد خرید خالی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        guest_info = {
            'name': request.data.get('name', ''),
            'phone': request.data.get('phone', ''),
            'address': request.data.get('address', ''),
            'postal_code': request.data.get('postal_code', ''),
            'shipping_cost': 0,  # D-080: ارسال رایگان در ظاهر
        }
        
        if not request.user.is_authenticated:
            if not guest_info['name'] or not guest_info['phone'] or not guest_info['address']:
                return Response(
                    {'error': 'برای خرید مهمان، نام، تلفن و آدرس الزامی است'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        try:
            from .checkout_service import CheckoutService
            order = CheckoutService.create_order(
                cart=cart,
                guest_info=guest_info,
                user=request.user if request.user.is_authenticated else None
            )
            serializer = OrderSerializer(order)
            return Response({
                'message': f'سفارش {order.order_number} با موفقیت ثبت شد',
                'order': serializer.data
            }, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PaymentViewSet(viewsets.ViewSet):
    """
    API پرداخت کارت‌به‌کارت (ADR-005 + D-067)
    
    Endpoints:
    - POST /payment/get-info/     : دریافت اطلاعات کارت مقصد (مشتری)
    - POST /payment/submit-evidence/ : ثبت evidence پرداخت (مشتری - ۳ فیلد اجباری)
    - GET  /payment/<id>/         : مشاهده وضعیت پرداخت
    - POST /payment/admin-confirm/ : تایید پرداخت توسط ادمین
    - POST /payment/admin-reject/  : رد پرداخت توسط ادمین
    """
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    
    def get_permissions(self):
        """سطوح دسترسی متفاوت برای endpoints مختلف"""
        if self.action in ['admin_confirm', 'admin_reject']:
            return [IsAdminUser()]
        return [AllowAny()]
    
    @action(detail=False, methods=['post'], url_path='get-info')
    def get_payment_info(self, request):
        """
        دریافت اطلاعات کارت مقصد برای مشتری
        
        Body: {order_number: "RH-1405-00001"}
        Returns: اطلاعات حساب مقصد + مبلغ + راهنما
        """
        order_number = request.data.get('order_number')
        if not order_number:
            return Response({'error': 'order_number الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            return Response({'error': 'سفارش یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        
        # چک مالکیت سفارش
        if request.user.is_authenticated:
            if order.user != request.user:
                return Response({'error': 'دسترسی غیرمجاز'}, status=status.HTTP_403_FORBIDDEN)
        else:
            if order.session_key != request.session.session_key:
                return Response({'error': 'دسترسی غیرمجاز'}, status=status.HTTP_403_FORBIDDEN)
        
        # سفارش باید در وضعیت DRAFT یا PENDING باشد
        if order.status not in [Order.OrderStatus.DRAFT, Order.OrderStatus.PENDING]:
            return Response({'error': 'این سفارش قابل پرداخت نیست'}, status=status.HTTP_400_BAD_REQUEST)
        
        # دریافت اطلاعات حساب مقصد از Gateway
        gateway = get_payment_gateway()
        payment_info = gateway.create_payment(order)
        
        # ایجاد تراکنش Payment با وضعیت PENDING
        payment, created = Payment.objects.get_or_create(
            order=order,
            status=Payment.PaymentStatus.PENDING,
            defaults={
                'amount': order.total_price,
                'gateway': Payment.PaymentGateway.MANUAL,
            }
        )
        
        return Response({
            'message': 'اطلاعات پرداخت آماده است',
            'payment_id': str(payment.id),
            'payment_info': payment_info,
        })
    
    @action(detail=False, methods=['post'], url_path='submit-evidence')
    def submit_evidence(self, request):
        """
        ثبت evidence پرداخت توسط مشتری (D-067)
        
        ۳ evidence اجباری:
        - sender_card_last4: ۴ رقم آخر کارت فرستنده (string, 4 digits)
        - transfer_time: زمان واریز (ISO 8601 datetime)
        - amount: مبلغ واریزی (باید با مبلغ سفارش منطبق باشد)
        
        ۱ evidence اختیاری:
        - receipt_image: تصویر رسید (فایل - در صورت threshold اجباری می‌شود)
        """
        payment_id = request.data.get('payment_id')
        if not payment_id:
            return Response({'error': 'payment_id الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            payment = Payment.objects.get(id=payment_id)
        except (ObjectDoesNotExist, ValueError):
            return Response({'error': 'تراکنش پرداخت یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        
        # چک مالکیت: فقط مالک سفارش می‌تواند evidence ثبت کند
        order = payment.order
        if request.user.is_authenticated:
            if order.user != request.user:
                return Response({'error': 'دسترسی غیرمجاز'}, status=status.HTTP_403_FORBIDDEN)
        else:
            if order.session_key != request.session.session_key:
                return Response({'error': 'دسترسی غیرمجاز'}, status=status.HTTP_403_FORBIDDEN)
        
        # فقط پرداخت‌های PENDING قابل submit هستند
        if payment.status != Payment.PaymentStatus.PENDING:
            return Response(
                {'error': f'این پرداخت در وضعیت {payment.get_status_display()} است و قابل ارسال evidence نیست'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # دریافت evidence از request
        sender_card_last4 = request.data.get('sender_card_last4', '')
        transfer_time = request.data.get('transfer_time')
        amount = request.data.get('amount')
        receipt_image = request.FILES.get('receipt_image')
        
        # اعتبارسنجی‌های پایه
        if not sender_card_last4:
            return Response({'error': '۴ رقم آخر کارت الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not transfer_time:
            return Response({'error': 'زمان واریز الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not amount:
            return Response({'error': 'مبلغ واریزی الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        # استفاده از Gateway برای ثبت evidence
        try:
            gateway = get_payment_gateway()
            result = gateway.submit_evidence(
                payment=payment,
                evidence_data={
                    'sender_card_last4': sender_card_last4,
                    'transfer_time': transfer_time,
                    'amount': amount,
                    'receipt_image': receipt_image,
                }
            )
            
            logger.info(
                f"Evidence submitted for payment {payment.id}: "
                f"card_last4={sender_card_last4}"
            )
            
            return Response({
                'message': result.get('message', 'اطلاعات پرداخت با موفقیت ثبت شد'),
                'status': result.get('status'),
                'payment_id': str(payment.id),
                'order_number': payment.order.order_number,
                'next_steps': 'لطفاً منتظر تایید ادمین بمانید. وضعیت سفارش شما را از طریق ایمیل/پیامک اطلاع‌رسانی خواهیم کرد.'
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error submitting evidence: {e}")
            return Response({'error': 'خطا در ثبت اطلاعات پرداخت'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def retrieve(self, request, pk=None):
        """مشاهده وضعیت یک پرداخت خاص"""
        try:
            payment = Payment.objects.get(id=pk)
        except (ObjectDoesNotExist, ValueError):
            return Response({'error': 'تراکنش یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        
        # چک مالکیت
        order = payment.order
        if request.user.is_authenticated:
            if order.user != request.user and not request.user.is_staff:
                return Response({'error': 'دسترسی غیرمجاز'}, status=status.HTTP_403_FORBIDDEN)
        else:
            if order.session_key != request.session.session_key:
                return Response({'error': 'دسترسی غیرمجاز'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = PaymentSerializer(payment)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], url_path='admin-confirm')
    def admin_confirm(self, request):
        """
        تایید پرداخت توسط ادمین (فقط ادمین)
        
        Body:
        - payment_id: شناسه پرداخت
        - notes: یادداشت ادمین (اختیاری)
        """
        payment_id = request.data.get('payment_id')
        notes = request.data.get('notes', '')
        
        if not payment_id:
            return Response({'error': 'payment_id الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            payment = Payment.objects.get(id=payment_id)
        except (ObjectDoesNotExist, ValueError):
            return Response({'error': 'تراکنش پرداخت یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        
        # فقط پرداخت‌های PENDING_REVIEW قابل تایید هستند
        if payment.status != Payment.PaymentStatus.PENDING_REVIEW:
            return Response(
                {'error': f'فقط پرداخت‌های در انتظار تایید قابل تایید هستند. وضعیت فعلی: {payment.get_status_display()}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # تایید پرداخت
        payment.confirm(admin_user=request.user, notes=notes)
        
        # به‌روزرسانی وضعیت سفارش به PAID
        order = payment.order
        order.status = Order.OrderStatus.PAID
        order.save()
        
        logger.info(
            f"Payment {payment.id} confirmed by admin {request.user.username}"
        )
        
        return Response({
            'message': f'پرداخت سفارش {order.order_number} با موفقیت تایید شد',
            'order_number': order.order_number,
            'order_status': order.get_status_display(),
            'payment_status': payment.get_status_display(),
        })
    
    @action(detail=False, methods=['post'], url_path='admin-reject')
    def admin_reject(self, request):
        """
        رد پرداخت توسط ادمین (فقط ادمین)
        
        Body:
        - payment_id: شناسه پرداخت
        - notes: دلیل رد (الزامی)
        """
        payment_id = request.data.get('payment_id')
        notes = request.data.get('notes', '')
        
        if not payment_id:
            return Response({'error': 'payment_id الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not notes:
            return Response({'error': 'ذکر دلیل رد پرداخت الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            payment = Payment.objects.get(id=payment_id)
        except (ObjectDoesNotExist, ValueError):
            return Response({'error': 'تراکنش پرداخت یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        
        # فقط پرداخت‌های PENDING_REVIEW قابل رد هستند
        if payment.status != Payment.PaymentStatus.PENDING_REVIEW:
            return Response(
                {'error': f'فقط پرداخت‌های در انتظار تایید قابل رد هستند. وضعیت فعلی: {payment.get_status_display()}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # رد پرداخت
        payment.reject(admin_user=request.user, notes=notes)
        
        # سفارش در وضعیت PENDING می‌ماند (مشتری می‌تواند دوباره تلاش کند)
        
        logger.info(
            f"Payment {payment.id} rejected by admin {request.user.username}: {notes}"
        )
        
        return Response({
            'message': f'پرداخت سفارش {payment.order.order_number} رد شد',
            'order_number': payment.order.order_number,
            'payment_status': payment.get_status_display(),
        })


class AddressViewSet(viewsets.ModelViewSet):
    """API مدیریت آدرس‌های کاربر"""
    serializer_class = AddressSerializer
    http_method_names = ['get', 'post', 'put', 'delete']
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Address.objects.filter(user=self.request.user)
        return Address.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class OrderViewSet(viewsets.ModelViewSet):
    """
    API مشاهده سفارشات کاربر (فقط خواندنی)
    - GET /orders/              : لیست سفارشات کاربر
    - GET /orders/{order_number}/ : جزئیات یک سفارش
    """
    serializer_class = OrderSerializer
    http_method_names = ['get']
    lookup_field = 'order_number'
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Order.objects.filter(user=self.request.user).order_by('-created_at')
        return Order.objects.none()
    
    def retrieve(self, request, *args, **kwargs):
        order_number = kwargs.get('order_number')
        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            return Response({'error': 'سفارش یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        
        # چک مالکیت
        if not request.user.is_authenticated:
            if order.session_key != request.session.session_key:
                return Response({'error': 'دسترسی غیرمجاز'}, status=status.HTTP_403_FORBIDDEN)
        else:
            if order.user != request.user and not request.user.is_staff:
                return Response({'error': 'دسترسی غیرمجاز'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = OrderSerializer(order)
        return Response(serializer.data)
