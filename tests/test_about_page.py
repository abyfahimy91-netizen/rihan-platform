from django.test import TestCase, Client
from django.urls import reverse

class AboutPageTestCase(TestCase):
    def test_about_page_rendering_and_pillars(self):
        c = Client()
        res = c.get(reverse('about'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "ریهان یک گزینش‌گر امین است")
        self.assertContains(res, "۵ ستون گزینش کالا")
        self.assertContains(res, "اصالت و مبدأ روشن")
        self.assertContains(res, "آزمون کیفیت و آزمایشگاه")
        self.assertContains(res, "کرامت و آرامش خریدار")
        # Verify Independent Brand Rule
        self.assertNotContains(res, "عبدالحسین فهیمی")
