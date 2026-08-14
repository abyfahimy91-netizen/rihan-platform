from apps.catalog.models import Product

CART_SESSION_ID = 'rihan_cart'

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(CART_SESSION_ID)
        if not cart:
            cart = self.session[CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, product, quantity=1, override_quantity=False):
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] = {
                'quantity': 0,
                'price': int(product.price),
                'title': product.title,
                'slug': product.slug,
                'image_url': product.primary_image.image_url if product.primary_image else ''
            }
        if override_quantity:
            self.cart[product_id]['quantity'] = int(quantity)
        else:
            self.cart[product_id]['quantity'] += int(quantity)
        
        if self.cart[product_id]['quantity'] <= 0:
            self.remove(product)
        else:
            self.save()

    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def save(self):
        self.session.modified = True

    def clear(self):
        if CART_SESSION_ID in self.session:
            del self.session[CART_SESSION_ID]
            self.save()

    def __iter__(self):
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        cart = self.cart.copy()
        for product in products:
            cart[str(product.id)]['product'] = product
        for item in cart.values():
            if 'product' in item:
                item['total_price'] = item['price'] * item['quantity']
                yield item

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        return sum(item['price'] * item['quantity'] for item in self.cart.values())

    def get_shipping_cost(self):
        # مصوبه D-046: هزینه ارسال در قیمت تمام‌شده کالا محاسبه شده است (پرداخت مازاد صفر)
        return 0

    def get_grand_total(self):
        return self.get_total_price() + self.get_shipping_cost()
