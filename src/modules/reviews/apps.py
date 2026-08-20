"""
AppConfig for Reviews Module (M8)
"""
from django.apps import AppConfig


class ReviewsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.modules.reviews'
    label = 'reviews'
    verbose_name = "Reviews Module (M8)"
