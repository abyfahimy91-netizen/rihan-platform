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
