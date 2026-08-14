from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from rest_framework import generics, status
from rest_framework.response import Response
from apps.catalog.models import Product
from .models import Order, OrderItem
from .cart import Cart
from .serializers import OrderSerializer

def cart_detail_view(request):
    cart = Cart(request)
    context = {'cart': cart}
    if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
        return render(request, 'orders/partials/cart_content.html', context)
    return render(request, 'orders/cart.html', context)

@require_POST
def cart_add_view(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id, is_available=True)
    quantity = int(request.POST.get('quantity', 1))
    cart.add(product=product, quantity=quantity)
    if request.headers.get('HX-Request'):
        return render(request, 'orders/partials/cart_content.html', {'cart': cart})
    return redirect('cart_detail')

@require_POST
def cart_remove_view(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    if request.headers.get('HX-Request'):
        return render(request, 'orders/partials/cart_content.html', {'cart': cart})
    return redirect('cart_detail')

def checkout_view(request):
    cart = Cart(request)
    if len(cart) == 0:
        return redirect('product_list')

    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        province = request.POST.get('province')
        city = request.POST.get('city')
        address = request.POST.get('address')
        postal_code = request.POST.get('postal_code')
        notes = request.POST.get('notes', '')

        if name and phone and address and postal_code:
            order = Order.objects.create(
                customer_name=name,
                customer_phone=phone,
                province=province or 'نامشخص',
                city=city or 'نامشخص',
                shipping_address=address,
                postal_code=postal_code,
                customer_notes=notes,
                items_total=cart.get_total_price(),
                shipping_cost=0,
                grand_total=cart.get_grand_total(),
                status='pending_payment',
                payment_method='card_to_card'
            )

            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    product_title=item['product'].title,
                    product_sku=item['product'].sku,
                    unit_price=item['price'],
                    quantity=item['quantity'],
                    subtotal=item['total_price']
                )

            cart.clear()
            return redirect('order_success', order_number=order.order_number)

    context = {'cart': cart}
    return render(request, 'orders/checkout.html', context)

def order_success_view(request, order_number):
    order = get_object_or_404(Order.objects.prefetch_related('items'), order_number=order_number)
    return render(request, 'orders/order_success.html', {'order': order})

class OrderCreateAPI(generics.CreateAPIView):
    serializer_class = OrderSerializer
    def create(self, request, *args, **kwargs):
        cart = Cart(request)
        if len(cart) == 0:
            return Response({"error": "سبد خرید خالی است."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save(
            items_total=cart.get_total_price(),
            shipping_cost=0,
            grand_total=cart.get_grand_total(),
            status='pending_payment'
        )
        for item in cart:
            OrderItem.objects.create(
                order=order,
                product=item['product'],
                product_title=item['product'].title,
                product_sku=item['product'].sku,
                unit_price=item['price'],
                quantity=item['quantity']
            )
        cart.clear()
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
