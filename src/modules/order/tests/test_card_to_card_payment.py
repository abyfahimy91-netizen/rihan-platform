"""
Comprehensive tests for Card-to-Card Payment (ADR-005 + D-067)

Covers:
- Submit evidence with 3 required fields
- Admin confirm/reject
- Receipt threshold logic
- Dynamic order number with jdatetime
- Transparent pricing (free shipping appearance)
- Full E2E flow
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import Mock
from datetime import timedelta

from src.modules.catalog.models import Category, Supplier, Product, Inventory
from src.modules.order.models import Cart, CartItem, Order, Payment
from src.modules.order.services import get_or_create_cart, add_to_cart
from src.modules.order.checkout_service import CheckoutService
from src.modules.order.payment_gateway import (
    get_payment_gateway,
    CardToCardGateway,
)

User = get_user_model()


class CardToCardPaymentTest(TestCase):
    """Test suite for card-to-card payment flow (D-067, ADR-005)"""
    
    def setUp(self):
        """Set up test data"""
        # Users
        self.customer = User.objects.create_user(
            username='test_customer',
            password='test123456',
            email='test@rihan.local'
        )
        self.admin = User.objects.create_superuser(
            username='admin',
            password='admin123456',
            email='admin@rihan.local'
        )
        
        # Category and Supplier
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        self.supplier = Supplier.objects.create(
            title='Test Supplier',
            city='Test City'
        )
        
        # Product with inventory
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=self.category,
            supplier=self.supplier,
            unit='عدد',
            base_price=Decimal('100000'),
            shipping_cost=Decimal('20000'),
            margin_percent=20,
            short_description='Test product',
            origin_story='Test story',
            status='active',
        )
        self.product.final_price = self.product.calculate_final_price()
        self.product.save()
        
        # Inventory - استفاده از get_or_create به جای create
        # چون ممکن است از طریق signal ساخته شده باشد
        self.inventory, _ = Inventory.objects.get_or_create(
            product=self.product,
            defaults={
                'quantity': Decimal('100'),
                'reserved_quantity': Decimal('0'),
                'unit': 'عدد',
                'low_stock_threshold': Decimal('10'),
            }
        )
        
        # اگر inventory از قبل وجود داشت، موجودی را به 100 reset کن
        self.inventory.quantity = Decimal('100')
        self.inventory.reserved_quantity = Decimal('0')
        self.inventory.save()
        
        # Test client
        self.client = Client()
    
    def _create_order(self, quantity=2):
        """Helper: create order from cart"""
        request = Mock()
        request.user = self.customer
        request.session = Mock()
        request.session.session_key = f'test-{timezone.now().timestamp()}'
        
        cart = get_or_create_cart(request)
        add_to_cart(cart, str(self.product.id), quantity=quantity)
        
        order = CheckoutService.create_order(
            cart=cart,
            guest_info={
                'name': 'Test Customer',
                'phone': '09121234567',
                'address': 'Tehran',
                'postal_code': '1234567890',
            },
            user=self.customer
        )
        return order
    
    def _create_payment(self, order):
        """Helper: create pending payment"""
        return Payment.objects.create(
            order=order,
            amount=order.total_price,
            gateway=Payment.PaymentGateway.MANUAL,
            status=Payment.PaymentStatus.PENDING,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # Test 1: Submit evidence with valid data
    # ═══════════════════════════════════════════════════════════════
    def test_submit_evidence_success(self):
        """Customer can submit valid evidence (3 required fields)"""
        order = self._create_order(quantity=2)
        payment = self._create_payment(order)
        gateway = get_payment_gateway()
        
        result = gateway.submit_evidence(
            payment=payment,
            evidence_data={
                'sender_card_last4': '1234',
                'transfer_time': timezone.now(),
                'amount': order.total_price,
                'receipt_image': None,
            }
        )
        
        self.assertEqual(result['status'], 'PENDING_REVIEW')
        self.assertIn('message', result)
        
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.PaymentStatus.PENDING_REVIEW)
        self.assertEqual(payment.sender_card_last4, '1234')
        self.assertIsNotNone(payment.transfer_time)
    
    # ═══════════════════════════════════════════════════════════════
    # Test 2: Submit evidence with invalid card number
    # ═══════════════════════════════════════════════════════════════
    def test_submit_evidence_invalid_card(self):
        """Invalid card number (not 4 digits) is rejected"""
        order = self._create_order()
        payment = self._create_payment(order)
        gateway = get_payment_gateway()
        
        with self.assertRaises(ValueError) as ctx:
            gateway.submit_evidence(
                payment=payment,
                evidence_data={
                    'sender_card_last4': '12',  # Only 2 digits
                    'transfer_time': timezone.now(),
                    'amount': order.total_price,
                }
            )
        
        self.assertIn('۴ رقم', str(ctx.exception))
    
    # ═══════════════════════════════════════════════════════════════
    # Test 3: Submit evidence with wrong amount
    # ═══════════════════════════════════════════════════════════════
    def test_submit_evidence_wrong_amount(self):
        """Amount mismatch is rejected"""
        order = self._create_order()
        payment = self._create_payment(order)
        gateway = get_payment_gateway()
        
        wrong_amount = order.total_price + Decimal('50000')
        
        with self.assertRaises(ValueError) as ctx:
            gateway.submit_evidence(
                payment=payment,
                evidence_data={
                    'sender_card_last4': '4321',
                    'transfer_time': timezone.now(),
                    'amount': wrong_amount,
                }
            )
        
        self.assertIn('منطبق نیست', str(ctx.exception))
    
    # ═══════════════════════════════════════════════════════════════
    # Test 4: Submit evidence without transfer time
    # ═══════════════════════════════════════════════════════════════
    def test_submit_evidence_without_transfer_time(self):
        """Missing transfer_time is rejected"""
        order = self._create_order()
        payment = self._create_payment(order)
        gateway = get_payment_gateway()
        
        with self.assertRaises(ValueError) as ctx:
            gateway.submit_evidence(
                payment=payment,
                evidence_data={
                    'sender_card_last4': '5678',
                    'transfer_time': None,  # Missing
                    'amount': order.total_price,
                }
            )
        
        self.assertIn('زمان واریز', str(ctx.exception))
    
    # ═══════════════════════════════════════════════════════════════
    # Test 5: Admin confirm payment
    # ═══════════════════════════════════════════════════════════════
    def test_admin_confirm_payment(self):
        """Admin can confirm payment (Reservation → Sale)"""
        order = self._create_order(quantity=3)
        payment = self._create_payment(order)
        gateway = get_payment_gateway()
        
        # Submit evidence
        gateway.submit_evidence(
            payment=payment,
            evidence_data={
                'sender_card_last4': '9999',
                'transfer_time': timezone.now(),
                'amount': order.total_price,
            }
        )
        
        # Initial state
        self.inventory.refresh_from_db()
        self.assertEqual(float(self.inventory.reserved_quantity), 3.0)
        
        # Admin confirms
        CheckoutService.confirm_payment(
            order=order,
            payment=payment,
            payment_data={'notes': 'Test confirmation'},
            admin_user=self.admin,
        )
        
        # Check final state
        order.refresh_from_db()
        payment.refresh_from_db()
        self.inventory.refresh_from_db()
        
        self.assertEqual(order.status, Order.OrderStatus.PAID)
        self.assertEqual(payment.status, Payment.PaymentStatus.SUCCESS)
        self.assertEqual(payment.reviewed_by, self.admin)
        self.assertEqual(payment.sender_card_last4, '9999')  # Evidence preserved
        
        # Inventory: 100 → 97 (3 sold)
        self.assertEqual(float(self.inventory.quantity), 97.0)
        self.assertEqual(float(self.inventory.reserved_quantity), 0.0)
    
    # ═══════════════════════════════════════════════════════════════
    # Test 6: Admin reject payment
    # ═══════════════════════════════════════════════════════════════
    def test_admin_reject_payment(self):
        """Admin can reject payment with reason"""
        order = self._create_order()
        payment = self._create_payment(order)
        gateway = get_payment_gateway()
        
        gateway.submit_evidence(
            payment=payment,
            evidence_data={
                'sender_card_last4': '1111',
                'transfer_time': timezone.now(),
                'amount': order.total_price,
            }
        )
        
        payment.reject(
            admin_user=self.admin,
            notes='Receipt not clear'
        )
        
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.PaymentStatus.FAILED)
        self.assertEqual(payment.reviewed_by, self.admin)
        self.assertEqual(payment.admin_notes, 'Receipt not clear')
    
    # ═══════════════════════════════════════════════════════════════
    # Test 7: Receipt required above threshold
    # ═══════════════════════════════════════════════════════════════
    def test_receipt_required_above_threshold(self):
        """Receipt becomes required above configured threshold"""
        from django.conf import settings
        
        # Set threshold to 150,000
        original_threshold = getattr(settings, 'RECEIPT_REQUIRED_ABOVE', 0)
        settings.RECEIPT_REQUIRED_ABOVE = 150000
        
        try:
            # Create order with 2 items (200,000 total)
            order = self._create_order(quantity=2)
            payment = self._create_payment(order)
            gateway = get_payment_gateway()
            
            # Try to submit without receipt
            with self.assertRaises(ValueError) as ctx:
                gateway.submit_evidence(
                    payment=payment,
                    evidence_data={
                        'sender_card_last4': '2222',
                        'transfer_time': timezone.now(),
                        'amount': order.total_price,
                        'receipt_image': None,  # Missing but required
                    }
                )
            
            self.assertIn('رسید اجباری', str(ctx.exception))
        finally:
            settings.RECEIPT_REQUIRED_ABOVE = original_threshold
    
    # ═══════════════════════════════════════════════════════════════
    # Test 8: Dynamic order number with jdatetime
    # ═══════════════════════════════════════════════════════════════
    def test_dynamic_order_number_jdatetime(self):
        """Order number uses current Persian year from jdatetime"""
        import jdatetime
        
        order = self._create_order()
        current_year = str(jdatetime.date.today().year)
        
        self.assertTrue(order.order_number.startswith(f'RH-{current_year}-'))
        # Format: RH-YYYY-XXXXX
        parts = order.order_number.split('-')
        self.assertEqual(len(parts), 3)
        self.assertEqual(parts[0], 'RH')
        self.assertEqual(parts[1], current_year)
        self.assertEqual(len(parts[2]), 5)
    
    # ═══════════════════════════════════════════════════════════════
    # Test 9: Transparent pricing (free shipping appearance)
    # ═══════════════════════════════════════════════════════════════
    def test_transparent_pricing_free_shipping(self):
        """Shipping cost is hidden in final price (D-080)"""
        order = self._create_order(quantity=2)
        
        # Shipping cost should be 0 in the order (hidden in base price)
        self.assertEqual(float(order.shipping_cost), 0.0)
        
        # Total price equals subtotal (no separate shipping)
        self.assertEqual(order.total_price, order.subtotal)
    
    # ═══════════════════════════════════════════════════════════════
    # Test 10: Full E2E flow
    # ═══════════════════════════════════════════════════════════════
    def test_full_e2e_flow(self):
        """Complete flow: cart → order → evidence → admin confirm"""
        # Initial state
        self.assertEqual(float(self.inventory.quantity), 100.0)
        self.assertEqual(float(self.inventory.reserved_quantity), 0.0)
        
        # Create order (Reservation)
        order = self._create_order(quantity=5)
        payment = self._create_payment(order)
        
        # Check reservation
        self.inventory.refresh_from_db()
        self.assertEqual(float(self.inventory.reserved_quantity), 5.0)
        self.assertEqual(order.status, Order.OrderStatus.PENDING)
        
        # Submit evidence
        gateway = get_payment_gateway()
        result = gateway.submit_evidence(
            payment=payment,
            evidence_data={
                'sender_card_last4': '8888',
                'transfer_time': timezone.now(),
                'amount': order.total_price,
            }
        )
        
        self.assertEqual(result['status'], 'PENDING_REVIEW')
        
        # Admin confirms
        CheckoutService.confirm_payment(
            order=order,
            payment=payment,
            admin_user=self.admin,
        )
        
        # Final state
        order.refresh_from_db()
        payment.refresh_from_db()
        self.inventory.refresh_from_db()
        
        self.assertEqual(order.status, Order.OrderStatus.PAID)
        self.assertEqual(payment.status, Payment.PaymentStatus.SUCCESS)
        self.assertEqual(float(self.inventory.quantity), 95.0)  # 100 - 5
        self.assertEqual(float(self.inventory.reserved_quantity), 0.0)
    
    # ═══════════════════════════════════════════════════════════════
    # Test 11: Gateway type is MANUAL by default
    # ═══════════════════════════════════════════════════════════════
    def test_default_gateway_is_manual(self):
        """Default gateway is CardToCard (MANUAL)"""
        gateway = get_payment_gateway()
        self.assertIsInstance(gateway, CardToCardGateway)
        self.assertEqual(gateway.get_gateway_name(), 'MANUAL')
    
    # ═══════════════════════════════════════════════════════════════
    # Test 12: Payment page renders correctly
    # ═══════════════════════════════════════════════════════════════
    def test_payment_page_renders(self):
        """Payment page renders with card info"""
        order = self._create_order()
        self._create_payment(order)
        
        self.client.force_login(self.customer)
        response = self.client.get(f'/order/payment/{order.order_number}/')
        
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('کارت به کارت — واریز به یکی از کارت‌های زیر', content)
        self.assertIn('۴ رقم آخر کارت', content)

    # ═══════════════════════════════════════════════════════════════
    # Test 12b: Amount must be Rial (D-101)
    # ═══════════════════════════════════════════════════════════════
    def test_payment_page_amount_in_rial(self):
        """مبلغ قابل کپی و نمایش باید ریال باشد — اپ‌های بانکی مبلغ را ریال می‌پذیرند (D-101)"""
        order = self._create_order()
        self._create_payment(order)

        self.client.force_login(self.customer)
        response = self.client.get(f'/order/payment/{order.order_number}/')
        content = response.content.decode('utf-8')

        expected_rial = str(int(order.total_price * 10))
        # دکمه کپی، مقدار ریال تمیز (بدون اعشار) کپی می‌کند
        self.assertIn(f'data-copy="{expected_rial}"', content)
        self.assertNotIn(f'data-copy="{expected_rial}.', content)
        # واحد نمایش ریال است + معادل تومان هم هست
        self.assertIn('ریال', content)
        self.assertIn('معادل', content)
        # مقدار تومان خام دیگر کپی نمی‌شود
        self.assertNotIn(f'data-copy="{int(order.total_price)}"', content)
        # راهنمای قدیمی «به تومان واریز کنید» حذف شده
        self.assertNotIn('به <b>تومان</b> واریز', content)

    def test_payment_page_section_order_matches_bank_app(self):
        """ترتیب صفحه باید مطابق اپ بانکی باشد: ۱) کارت به کارت ۲) مبلغ ۳) ۴ رقم (D-101)"""
        order = self._create_order()
        self._create_payment(order)

        self.client.force_login(self.customer)
        response = self.client.get(f'/order/payment/{order.order_number}/')
        content = response.content.decode('utf-8')

        i_card = content.index('کارت به کارت — واریز به')
        i_amount = content.index('مبلغ واریز')
        i_last4 = content.index('رسید پرداخت را ثبت کنید')
        self.assertLess(i_card, i_amount)
        self.assertLess(i_amount, i_last4)

        # راهنما هم همین ترتیب را می‌گوید
        i_g1 = content.index('۱) کارت به کارت')
        i_g2 = content.index('۲) مبلغ')
        i_g3 = content.index('۳) ثبت رسید')
        self.assertLess(i_g1, i_g2)
        self.assertLess(i_g2, i_g3)
    
    # ═══════════════════════════════════════════════════════════════
    # Test 13: Tracking page renders timeline
    # ═══════════════════════════════════════════════════════════════
    def test_tracking_page_renders_timeline(self):
        """Tracking page shows 5-step timeline"""
        order = self._create_order()
        
        self.client.force_login(self.customer)
        response = self.client.get(f'/order/tracking/{order.order_number}/')
        
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn(order.order_number, content)
        self.assertIn('سفارش ثبت شد', content)  # Step 1
    
    # ═══════════════════════════════════════════════════════════════
    # Test 14: Unauthorized access is forbidden
    # ═══════════════════════════════════════════════════════════════
    def test_unauthorized_access_forbidden(self):
        """Non-owner cannot access order pages"""
        order = self._create_order()
        
        other_user = User.objects.create_user(
            username='other_user',
            password='pass123'
        )
        
        self.client.force_login(other_user)
        response = self.client.get(f'/order/tracking/{order.order_number}/')
        
        self.assertEqual(response.status_code, 403)
