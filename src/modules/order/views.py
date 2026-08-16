from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from .services import get_or_create_cart, add_to_cart, update_cart_item, remove_from_cart
from .serializers import CartSerializer


class CartViewSet(viewsets.ViewSet):
    '''
    API سبد خرید
    - GET  /cart/             : مشاهده سبد
    - POST /cart/add/         : افزودن کالا
    - PUT  /cart/update/<id>/ : به‌روزرسانی تعداد
    - DEL  /cart/remove/<id>/ : حذف کالا
    '''
    
    def list(self, request):
        '''مشاهده سبد خرید فعلی کاربر/مهمان'''
        cart = get_or_create_cart(request)
        serializer = CartSerializer(cart)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def add(self, request):
        '''افزودن کالا به سبد خرید'''
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        
        if not product_id:
            return Response(
                {'error': 'product_id الزامی است'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
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
        '''به‌روزرسانی تعداد یک کالا'''
        item_id = request.data.get('item_id')
        quantity = request.data.get('quantity')
        
        if not item_id or quantity is None:
            return Response(
                {'error': 'item_id و quantity الزامی هستند'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            cart = get_or_create_cart(request)
            update_cart_item(cart, item_id, int(quantity))
            serializer = CartSerializer(cart)
            return Response({
                'message': 'سبد به‌روزرسانی شد',
                'cart': serializer.data
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['delete'])
    def remove(self, request):
        '''حذف یک کالا از سبد'''
        item_id = request.data.get('item_id')
        if not item_id:
            return Response({'error': 'item_id الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cart = get_or_create_cart(request)
            remove_from_cart(cart, item_id)
            serializer = CartSerializer(cart)
            return Response({
                'message': 'کالا حذف شد',
                'cart': serializer.data
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def checkout(self, request):
        '''
        نهایی‌سازی سفارش
        Body: {name, phone, address, postal_code, shipping_cost}
        '''
        from .services import create_order_from_cart
        from .serializers import OrderSerializer
        
        cart = get_or_create_cart(request)
        
        if not cart.items.exists():
            return Response(
                {'error': 'سبد خرید خالی است'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        guest_info = {
            'name': request.data.get('name', ''),
            'phone': request.data.get('phone', ''),
            'address': request.data.get('address', ''),
            'postal_code': request.data.get('postal_code', ''),
            'shipping_cost': request.data.get('shipping_cost', 0),
        }
        
        # اعتبارسنجی اطلاعات مهمان (برای کاربر لاگین‌کرده اجباری نیست)
        if not request.user.is_authenticated:
            if not guest_info['name'] or not guest_info['phone'] or not guest_info['address']:
                return Response(
                    {'error': 'برای خرید مهمان، نام، تلفن و آدرس الزامی است'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        try:
            order = create_order_from_cart(cart, guest_info)
            serializer = OrderSerializer(order)
            return Response({
                'message': f'سفارش {order.order_number} با موفقیت ثبت شد',
                'order': serializer.data
            }, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PaymentViewSet(viewsets.ViewSet):
    '''
    API پرداخت
    - POST /payment/create/  : ایجاد پرداخت (بازگشت URL درگاه)
    - POST /payment/verify/  : تایید پرداخت پس از بازگشت از درگاه
    '''
    
    @action(detail=False, methods=['post'])
    def create(self, request):
        '''ایجاد تراکنش پرداخت'''
        from .models import Order, Payment
        from .payment_gateway import get_payment_gateway
        
        order_number = request.data.get('order_number')
        if not order_number:
            return Response({'error': 'order_number الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            return Response({'error': 'سفارش یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        
        # چک مالکیت سفارش
        if request.user.is_authenticated and order.user != request.user:
            return Response({'error': 'دسترسی غیرمجاز'}, status=status.HTTP_403_FORBIDDEN)
        
        if order.status != Order.OrderStatus.DRAFT:
            return Response({'error': 'این سفارش قابل پرداخت نیست'}, status=status.HTTP_400_BAD_REQUEST)
        
        # ایجاد تراکنش پرداخت
        payment = Payment.objects.create(
            order=order,
            amount=order.total_price,
            status=Payment.PaymentStatus.PENDING,
            gateway=get_payment_gateway().__class__.__name__.replace('PaymentGateway', '').upper()
        )
        
        # ایجاد پرداخت در درگاه
        gateway = get_payment_gateway()
        callback_url = f"{settings.FRONTEND_URL}/payment/callback"
        gateway_response = gateway.create_payment(
            amount=order.total_price,
            description=f"پرداخت سفارش {order.order_number}",
            callback_url=callback_url
        )
        
        payment.authority = gateway_response['authority']
        payment.save()
        
        # تغییر وضعیت سفارش به PENDING
        order.status = Order.OrderStatus.PENDING
        order.save()
        
        return Response({
            'message': 'تراکنش پرداخت ایجاد شد',
            'payment_id': payment.id,
            'payment_url': gateway_response['payment_url'],
            'gateway_message': gateway_response.get('message', ''),
            'order_number': order.order_number
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def verify(self, request):
        '''تایید پرداخت پس از بازگشت از درگاه'''
        from .models import Payment, Order
        from .payment_gateway import get_payment_gateway
        
        payment_id = request.data.get('payment_id')
        if not payment_id:
            return Response({'error': 'payment_id الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            payment = Payment.objects.get(id=payment_id)
        except Payment.DoesNotExist:
            return Response({'error': 'تراکنش پرداخت یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        
        if payment.status != Payment.PaymentStatus.PENDING:
            return Response({'error': f'این پرداخت قبلاً {payment.get_status_display()} شده است'}, status=status.HTTP_400_BAD_REQUEST)
        
        # تایید پرداخت از درگاه
        gateway = get_payment_gateway()
        is_success = gateway.verify_payment(payment)
        
        order = payment.order
        
        if is_success:
            order.status = Order.OrderStatus.PAID
            order.save()
            
            return Response({
                'message': f'پرداخت سفارش {order.order_number} با موفقیت تایید شد',
                'order_number': order.order_number,
                'payment_status': payment.get_status_display(),
                'ref_id': payment.ref_id
            })
        else:
            order.status = Order.OrderStatus.DRAFT
            order.save()
            
            return Response({
                'message': 'پرداخت ناموفق بود',
                'order_number': order.order_number,
                'payment_status': payment.get_status_display()
            }, status=status.HTTP_400_BAD_REQUEST)
