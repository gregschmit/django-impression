"""
This module is for testing the rate limiting mechanism.
"""

from unittest import mock

from django.test import TestCase
from django.utils import timezone

from ..models import EmailAddress, RateLimit, Service


class RateLimitTestCase(TestCase):
    def setUp(self):
        self.from_email = EmailAddress.objects.create(email_address="from@example.org")
        self.test1 = EmailAddress.objects.create(email_address="test1@example.org")
        self.test2 = EmailAddress.objects.create(email_address="test2@example.org")
        self.rate_limit = RateLimit.objects.create(
            name="Test Limit",
            quantity=2,
            type=RateLimit.ROLLING_WINDOW,
            block_period=RateLimit.HOUR,
            rolling_window=timezone.timedelta(hours=1),
        )
        self.service = Service.objects.create(
            name="test_service", rate_limit=self.rate_limit
        )

    @mock.patch("django.utils.timezone.now")
    def test_get_timeframe_rolling_window(self, mock_now):
        mock_now.return_value = timezone.datetime(2019, 12, 11, 4, 32, 45)
        (then, now) = self.rate_limit.get_timeframe()
        self.assertEqual(then, timezone.datetime(2019, 12, 11, 3, 32, 45))
        self.assertEqual(now, timezone.datetime(2019, 12, 11, 4, 32, 45))

    @mock.patch("django.utils.timezone.now")
    def test_get_timeframe_block_hour(self, mock_now):
        self.rate_limit.type = RateLimit.BLOCK_PERIOD
        self.rate_limit.save()
        mock_now.return_value = timezone.datetime(2019, 12, 11, 4, 32, 45)
        (then, now) = self.rate_limit.get_timeframe()
        self.assertEqual(then, timezone.datetime(2019, 12, 11, 4, 0, 0))
        self.assertEqual(now, timezone.datetime(2019, 12, 11, 4, 32, 45))

    @mock.patch("django.utils.timezone.now")
    def test_get_timeframe_block_day(self, mock_now):
        self.rate_limit.type = RateLimit.BLOCK_PERIOD
        self.rate_limit.block_period = RateLimit.DAY
        self.rate_limit.save()
        mock_now.return_value = timezone.datetime(2019, 12, 11, 4, 32, 45)
        (then, now) = self.rate_limit.get_timeframe()
        self.assertEqual(then, timezone.datetime(2019, 12, 11, 0, 0, 0))
        self.assertEqual(now, timezone.datetime(2019, 12, 11, 4, 32, 45))

    @mock.patch("django.utils.timezone.now")
    def test_get_timeframe_block_week(self, mock_now):
        self.rate_limit.type = RateLimit.BLOCK_PERIOD
        self.rate_limit.block_period = RateLimit.WEEK
        self.rate_limit.save()
        mock_now.return_value = timezone.datetime(2019, 12, 11, 4, 32, 45)
        (then, now) = self.rate_limit.get_timeframe()
        self.assertEqual(then, timezone.datetime(2019, 12, 8, 0, 0, 0))
        self.assertEqual(now, timezone.datetime(2019, 12, 11, 4, 32, 45))

    @mock.patch("django.utils.timezone.now")
    def test_get_timeframe_block_month(self, mock_now):
        self.rate_limit.type = RateLimit.BLOCK_PERIOD
        self.rate_limit.block_period = RateLimit.MONTH
        self.rate_limit.save()
        mock_now.return_value = timezone.datetime(2019, 12, 11, 4, 32, 45)
        (then, now) = self.rate_limit.get_timeframe()
        self.assertEqual(then, timezone.datetime(2019, 12, 1, 0, 0, 0))
        self.assertEqual(now, timezone.datetime(2019, 12, 11, 4, 32, 45))

    @mock.patch("django.utils.timezone.now")
    def test_check_service_good(self, mock_now):
        self.rate_limit.type = RateLimit.BLOCK_PERIOD
        self.rate_limit.block_period = RateLimit.MONTH
        self.rate_limit.save()
        mock_now.return_value = timezone.datetime(2019, 12, 11, 4, 32, 45)
        (then, now) = self.rate_limit.get_timeframe()
        self.assertEqual(then, timezone.datetime(2019, 12, 1, 0, 0, 0))
        self.assertEqual(now, timezone.datetime(2019, 12, 11, 4, 32, 45))
