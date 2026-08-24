"""سوالات متداول پیش‌فرض — همان سه سوالی که قبلاً داخل قالب تماس هاردکد بود (D-100)"""
from django.db import migrations


DEFAULT_FAQS = [
    (
        'چگونه سفارش دهم؟',
        'محصول مورد نظر را انتخاب کنید، به سبد خرید اضافه کنید و مراحل تسویه‌حساب را طی کنید.',
    ),
    (
        'چگونه سفارشم را پیگیری کنم؟',
        'از صفحه «پیگیری سفارش» با شماره سفارش و شماره تلفن خود استفاده کنید.',
    ),
    (
        'آیا امکان مرجوعی وجود دارد؟',
        'بله، تا ۷ روز پس از تحویل می‌توانید محصول را مرجوع کنید. جزئیات کامل در صفحه «سیاست مرجوعی» آمده است.',
    ),
]


def seed_default_faqs(apps, schema_editor):
    FaqItem = apps.get_model('pages', 'FaqItem')
    if FaqItem.objects.exists():
        return  # اگر ادمین سوالی ثبت کرده، دست نمی‌زنیم
    for order, (question, answer) in enumerate(DEFAULT_FAQS, start=1):
        FaqItem.objects.create(
            question=question,
            answer=answer,
            sort_order=order,
            is_active=True,
        )


def unseed(apps, schema_editor):
    FaqItem = apps.get_model('pages', 'FaqItem')
    questions = {q for q, _ in DEFAULT_FAQS}
    FaqItem.objects.filter(question__in=questions).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0002_faqitem_sitesettings_about_body_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_default_faqs, unseed),
    ]
