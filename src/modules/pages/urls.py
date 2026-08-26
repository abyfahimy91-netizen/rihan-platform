from django.urls import path
from . import views

app_name = "pages"

urlpatterns = [
    path("about/", views.about_view, name="about"),
    path("contact/", views.contact_view, name="contact"),
    path("return-policy/", views.return_policy_view, name="return_policy"),
    path("faq/", views.faq_view, name="faq"),  # D-100: قبلاً لینک فوتر 404 می‌داد
    path("privacy/", views.privacy_view, name="privacy"),  # D-109: چک‌لیست اینماد
]
