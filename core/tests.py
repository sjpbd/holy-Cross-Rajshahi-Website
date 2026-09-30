import tempfile
from datetime import timedelta

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import PopupBanner

GIF = (
    b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00'
    b',\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PopupBannerTests(TestCase):
    def setUp(self):
        cache.clear()
        PopupBanner.objects.all().delete()

    def _banner(self, **kwargs):
        return PopupBanner.objects.create(
            title=kwargs.pop('title', 'Admission poster'),
            image=SimpleUploadedFile('poster.gif', GIF, content_type='image/gif'),
            **kwargs,
        )

    def test_homepage_shows_active_banner(self):
        banner = self._banner(link='/admission/', button_text='Apply Now')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.context['popup_banner'], banner)
        self.assertContains(response, banner.image.url)
        self.assertContains(response, 'Apply Now')

    def test_no_popup_when_inactive_or_outside_schedule(self):
        now = timezone.now()
        self._banner(is_active=False)
        self._banner(starts_at=now + timedelta(days=1))
        self._banner(ends_at=now - timedelta(days=1))
        response = self.client.get(reverse('home'))
        self.assertIsNone(response.context['popup_banner'])
        self.assertNotContains(response, 'popupBanner(')

    def test_button_hidden_without_link(self):
        self._banner(link='', button_text='Apply Now')
        response = self.client.get(reverse('home'))
        self.assertNotContains(response, 'Apply Now <i')
