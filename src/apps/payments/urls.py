from django.urls import path
from . import views

urlpatterns = [
    path('payments/receipt/upload/<str:order_number>/', views.upload_receipt_view, name='upload_receipt'),
]
