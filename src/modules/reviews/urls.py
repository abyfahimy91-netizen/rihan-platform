"""
URLs for Reviews Module (M8)
"""
from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    # Submit review (registered user, from product page)
    path(
        'submit/<str:product_slug>/',
        views.submit_review,
        name='submit_review'
    ),
    
    # Guest review via SMS token
    path(
        'guest/<str:token>/',
        views.guest_review_form,
        name='guest_review'
    ),
    
    # API: Get reviews for a product
    path(
        'api/product/<str:product_slug>/',
        views.product_reviews_api,
        name='product_reviews_api'
    ),
]
