"""
Tests for M8 - Reviews Module (US-009)

Covers:
- Review model validation
- can_review logic (DELIVERED orders only)
- Guest token (one-time, 7 days)
- Registered user review submission
- Guest review submission via token
- Admin approval workflow
- Reviews API
"""
from decimal import Decimal
from datetime import timedelta

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from src.modules.catalog.models import Product, Category, Supplier
from src.modules.order.models import Order, OrderItem
from src.modules.reviews.models import Review


User = get_user_model()


class ReviewModelTest(TestCase):
    """Test Review model methods and validation"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='09121111111',
            first_name='Test',
            last_name='User'
        )
        self.supplier = Supplier.objects.create(title='Test Supplier', city='Tehran')
        self.category = Category.objects.create(name='Test Cat', slug='test-cat')
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=self.category,
            supplier=self.supplier,
            base_price=Decimal('100000'),
            status='active'
        )
        self.order = Order.objects.create(
            user=self.user,
            status='DELIVERED',
            total_price=Decimal('100000')
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            unit_price_at_purchase=Decimal('100000'),
            product_name_snapshot=self.product.name
        )
    
    def test_can_review_delivered_order(self):
        """DELIVERED order should be reviewable"""
        can_review, message = Review.can_review(self.order)
        self.assertTrue(can_review)
    
    def test_cannot_review_pending_order(self):
        """PENDING order should NOT be reviewable"""
        pending_order = Order.objects.create(
            user=self.user,
            status='PENDING',
            total_price=Decimal('100000')
        )
        can_review, message = Review.can_review(pending_order)
        self.assertFalse(can_review)
        self.assertIn('تحویل‌شده', message)
    
    def test_cannot_review_twice(self):
        """Same order cannot be reviewed twice"""
        Review.objects.create(
            product=self.product,
            order=self.order,
            user=self.user,
            rating=5,
            text='Great product!'
        )
        can_review, message = Review.can_review(self.order)
        self.assertFalse(can_review)
        self.assertIn('قبلاً', message)
    
    def test_generate_guest_token(self):
        """Guest token should be unique and secure"""
        token1 = Review.generate_guest_token()
        token2 = Review.generate_guest_token()
        
        self.assertNotEqual(token1, token2)
        self.assertGreaterEqual(len(token1), 32)
    
    def test_token_validity(self):
        """Token should be valid within 7 days"""
        review = Review.objects.create(
            product=self.product,
            order=self.order,
            guest_name='Guest',
            rating=5,
            text='',
            guest_token=Review.generate_guest_token(),
            token_expires_at=timezone.now() + timedelta(days=7)
        )
        
        self.assertTrue(review.is_token_valid())
    
    def test_token_expired(self):
        """Token should be invalid after 7 days"""
        review = Review.objects.create(
            product=self.product,
            order=self.order,
            guest_name='Guest',
            rating=5,
            text='',
            guest_token=Review.generate_guest_token(),
            token_expires_at=timezone.now() - timedelta(days=1)  # Expired
        )
        
        self.assertFalse(review.is_token_valid())
    
    def test_token_one_time_use(self):
        """Token should be invalid after use"""
        review = Review.objects.create(
            product=self.product,
            order=self.order,
            guest_name='Guest',
            rating=5,
            text='',
            guest_token=Review.generate_guest_token(),
            token_expires_at=timezone.now() + timedelta(days=7)
        )
        
        review.use_token()
        self.assertFalse(review.is_token_valid())
    
    def test_approve_review(self):
        """Approve method should set approval fields"""
        admin = User.objects.create_user(username='admin', is_staff=True)
        review = Review.objects.create(
            product=self.product,
            order=self.order,
            user=self.user,
            rating=5,
            text='Great!'
        )
        
        self.assertFalse(review.is_approved)
        
        review.approve(admin)
        
        self.assertTrue(review.is_approved)
        self.assertEqual(review.approved_by, admin)
        self.assertIsNotNone(review.approved_at)
    
    def test_max_text_length(self):
        """Review text should be limited to 500 chars"""
        long_text = 'x' * 600
        review = Review.objects.create(
            product=self.product,
            order=self.order,
            user=self.user,
            rating=5,
            text=long_text[:500]
        )
        self.assertLessEqual(len(review.text), 500)


class GuestTokenWorkflowTest(TestCase):
    """Test guest review token workflow"""
    
    def setUp(self):
        self.supplier = Supplier.objects.create(title='Test Supplier', city='Tehran')
        self.category = Category.objects.create(name='Test Cat', slug='test-cat-guest')
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product-guest',
            category=self.category,
            supplier=self.supplier,
            base_price=Decimal('100000'),
            status='active'
        )
        self.guest_order = Order.objects.create(
            user=None,
            status='DELIVERED',
            guest_name='Guest Customer',
            guest_phone='09123333333',
            total_price=Decimal('100000')
        )
        OrderItem.objects.create(
            order=self.guest_order,
            product=self.product,
            quantity=1,
            unit_price_at_purchase=Decimal('100000'),
            product_name_snapshot=self.product.name
        )
    
    def test_create_guest_review_token(self):
        """create_guest_review_token should create placeholder review"""
        review, token = Review.create_guest_review_token(self.guest_order)
        
        self.assertIsNotNone(review)
        self.assertEqual(review.guest_token, token)
        self.assertEqual(review.guest_name, 'Guest Customer')
        self.assertEqual(review.guest_phone, '09123333333')
        self.assertFalse(review.token_used)
    
    def test_guest_review_via_token(self):
        """Guest can submit review via valid token"""
        client = Client()
        review, token = Review.create_guest_review_token(self.guest_order)
        
        response = client.post(f'/reviews/guest/{token}/', {
            'rating': '5',
            'title': 'Excellent!',
            'text': 'This product is amazing!'
        })
        
        self.assertEqual(response.status_code, 200)
        
        review.refresh_from_db()
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.text, 'This product is amazing!')
        self.assertTrue(review.token_used)
    
    def test_token_cannot_be_reused(self):
        """Used token should show expired page"""
        client = Client()
        review, token = Review.create_guest_review_token(self.guest_order)
        
        # First use
        client.post(f'/reviews/guest/{token}/', {
            'rating': '5',
            'text': 'First review'
        })
        
        # Second use should fail
        response = client.get(f'/reviews/guest/{token}/')
        self.assertContains(response, 'استفاده شده')
    
    def test_invalid_token_shows_404(self):
        """Invalid token should return 404"""
        client = Client()
        response = client.get('/reviews/guest/invalid-token-12345/')
        self.assertEqual(response.status_code, 404)
    
    def test_expired_token_shows_message(self):
        """Expired token should show expiration message"""
        client = Client()
        review, token = Review.create_guest_review_token(self.guest_order)
        
        # Manually expire the token
        review.token_expires_at = timezone.now() - timedelta(days=1)
        review.save()
        
        response = client.get(f'/reviews/guest/{token}/')
        self.assertContains(response, 'منقضی')


class RegisteredUserReviewTest(TestCase):
    """Test registered user review submission"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='09124444444',
            password='testpass123',
            first_name='Registered',
            last_name='User'
        )
        self.supplier = Supplier.objects.create(title='Test Supplier', city='Tehran')
        self.category = Category.objects.create(name='Test Cat', slug='test-cat-reg')
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product-reg',
            category=self.category,
            supplier=self.supplier,
            base_price=Decimal('100000'),
            status='active'
        )
        
        # Create a delivered order for this user
        self.order = Order.objects.create(
            user=self.user,
            status='DELIVERED',
            total_price=Decimal('100000')
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            unit_price_at_purchase=Decimal('100000'),
            product_name_snapshot=self.product.name
        )
    
    def test_user_without_delivered_order_cannot_review(self):
        """User without delivered order should see no_access page"""
        new_user = User.objects.create_user(
            username='09125555555',
            password='testpass123'
        )
        self.client.force_login(new_user)
        
        response = self.client.get(f'/reviews/submit/{self.product.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'عدم دسترسی')
    
    def test_user_with_delivered_order_can_access_form(self):
        """User with delivered order should see review form"""
        self.client.force_login(self.user)
        
        response = self.client.get(f'/reviews/submit/{self.product.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ثبت نظر')
    
    def test_submit_review_success(self):
        """Valid review submission should succeed"""
        self.client.force_login(self.user)
        
        response = self.client.post(f'/reviews/submit/{self.product.slug}/', {
            'rating': '5',
            'title': 'Excellent Product',
            'text': 'This is a great product!'
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        review = Review.objects.filter(user=self.user, product=self.product).first()
        self.assertIsNotNone(review)
        self.assertEqual(review.rating, 5)
        self.assertFalse(review.is_approved)  # Pending approval
    
    def test_submit_review_with_long_text_rejected(self):
        """Review with >500 chars should be rejected"""
        self.client.force_login(self.user)
        
        response = self.client.post(
            f'/reviews/submit/{self.product.slug}/',
            {
                'rating': '5',
                'text': 'x' * 600
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_cannot_review_same_product_twice(self):
        """User cannot review same product twice"""
        self.client.force_login(self.user)
        
        # First review
        self.client.post(f'/reviews/submit/{self.product.slug}/', {
            'rating': '5',
            'text': 'First review'
        })
        
        # Second attempt
        response = self.client.get(f'/reviews/submit/{self.product.slug}/')
        self.assertContains(response, 'قبلاً')


class ReviewsAPITest(TestCase):
    """Test reviews API endpoint"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='09126666666',
            first_name='API',
            last_name='Test'
        )
        self.supplier = Supplier.objects.create(title='Test Supplier', city='Tehran')
        self.category = Category.objects.create(name='Test Cat', slug='test-cat-api')
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product-api',
            category=self.category,
            supplier=self.supplier,
            base_price=Decimal('100000'),
            status='active'
        )
        self.order = Order.objects.create(
            user=self.user,
            status='DELIVERED',
            total_price=Decimal('100000')
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            unit_price_at_purchase=Decimal('100000'),
            product_name_snapshot=self.product.name
        )
    
    def test_api_returns_empty_for_no_reviews(self):
        """API should return empty list for product without reviews"""
        response = self.client.get(f'/reviews/api/product/{self.product.slug}/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['reviews'], [])
    
    def test_api_only_shows_approved_reviews(self):
        """API should only return approved reviews"""
        # Create unapproved review
        Review.objects.create(
            product=self.product,
            order=self.order,
            user=self.user,
            rating=5,
            text='Pending review',
            is_approved=False
        )
        
        response = self.client.get(f'/reviews/api/product/{self.product.slug}/')
        data = response.json()
        
        self.assertEqual(data['count'], 0)
    
    def test_api_shows_approved_reviews(self):
        """API should return approved reviews"""
        admin = User.objects.create_user(username='admin2', is_staff=True)
        review = Review.objects.create(
            product=self.product,
            order=self.order,
            user=self.user,
            rating=5,
            text='Approved review'
        )
        review.approve(admin)
        
        response = self.client.get(f'/reviews/api/product/{self.product.slug}/')
        data = response.json()
        
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['reviews'][0]['text'], 'Approved review')
        self.assertEqual(data['reviews'][0]['rating'], 5)
    
    def test_api_calculates_average_rating(self):
        """API should calculate average rating correctly"""
        admin = User.objects.create_user(username='admin3', is_staff=True)
        
        # Create order for second review
        order2 = Order.objects.create(
            user=self.user,
            status='DELIVERED',
            total_price=Decimal('200000')
        )
        OrderItem.objects.create(
            order=order2,
            product=self.product,
            quantity=1,
            unit_price_at_purchase=Decimal('100000'),
            product_name_snapshot=self.product.name
        )
        
        # Create two approved reviews
        r1 = Review.objects.create(
            product=self.product, order=self.order, user=self.user,
            rating=5, text='Great'
        )
        r1.approve(admin)
        
        user2 = User.objects.create_user(username='09127777777')
        r2 = Review.objects.create(
            product=self.product, order=order2, user=user2,
            rating=3, text='OK'
        )
        r2.approve(admin)
        
        response = self.client.get(f'/reviews/api/product/{self.product.slug}/')
        data = response.json()
        
        self.assertEqual(data['average_rating'], 4.0)  # (5+3)/2
