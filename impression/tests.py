"""
This module is for testing the email models, API, email backends, and template engine.

TODO: build more tests for Service and Message models.
"""

from unittest import mock

from django.test import TestCase
from django.utils import timezone

from .models import EmailAddress, Template, Distribution, RateLimit, Service


class EmailAddressTestCase(TestCase):
    """
    Tests for the EmailAddress model.
    """

    def setUp(self):
        self.email = EmailAddress.objects.create(email_address="john@example.org")

    def test_constructor_properties(self):
        self.assertEqual(self.email.email_address, "john@example.org")

    def test_extract_display_email(self):
        s = '"John C. Doe" <john@example.org>'
        e = "john@example.org"
        email = EmailAddress.extract_display_email(s)
        self.assertEqual(email, e)


class TemplateTestCase(TestCase):
    """
    Tests for the Template model.
    """

    def setUp(self):
        self.template = Template.objects.create(
            name="Test Template",
            subject="Test Subject",
            body="Test Body: {{ content }}",
            extends=None,
        )

    def test_constructor_properties(self):
        self.assertEqual(self.template.name, "Test Template")
        self.assertEqual(self.template.subject, "Test Subject")
        self.assertEqual(self.template.body, "Test Body: {{ content }}")
        self.assertIsNone(self.template.extends)


class DistributionTestCase(TestCase):
    """
    Tests for the Distribution model.
    """

    def setUp(self):
        self.test1 = EmailAddress.objects.create(email_address="test1@example.org")
        self.test2 = EmailAddress.objects.create(email_address="test2@example.org")
        self.all_emails = set([self.test1, self.test2])
        self.disti = Distribution.objects.create(name="Test Disti")
        self.disti.email_addresses.add(self.test1, self.test2)

        # build disti with duplicates
        self.dupe_disti = Distribution.objects.create(name="Dupe Disti")
        self.dupe_disti.email_addresses.add(self.test1, self.test2)
        self.dupe_disti.distributions.add(self.disti)

        # build disti with self reference
        self.self_disti = Distribution.objects.create(name="Self Disti")
        self.self_disti.email_addresses.add(self.test1)
        self.self_disti.distributions.add(self.self_disti)

        # build disti with cyclic reference
        self.cyclic_disti1 = Distribution.objects.create(name="Cyclic Disti 1")
        self.cyclic_disti1.email_addresses.add(self.test1)
        self.cyclic_disti2 = Distribution.objects.create(name="Cyclic Disti 2")
        self.cyclic_disti2.email_addresses.add(self.test2)
        self.cyclic_disti1.distributions.add(self.cyclic_disti2)
        self.cyclic_disti2.distributions.add(self.cyclic_disti1)

    def test_constructor_properties(self):
        self.assertEqual(self.disti.name, "Test Disti")
        emails = self.disti.email_addresses.all()
        self.assertIn(self.test1, emails)
        self.assertIn(self.test2, emails)

    def test_collect_distribution(self):
        """
        Test that emails are collected properly.
        """
        test_emails = self.disti.collect_email_addresses()
        self.assertEqual(len(test_emails), 2)
        self.assertSetEqual(self.all_emails, set(test_emails))

    def test_collect_distribution_with_duplicates(self):
        """
        Test that a distribution with duplicates to ensure it only collects each email
        once.
        """
        test_emails = self.dupe_disti.collect_email_addresses()
        self.assertEqual(len(test_emails), 2)
        self.assertSetEqual(self.all_emails, set(test_emails))

    def test_collect_distribution_with_self_references(self):
        """
        Test that a distribution with self references to ensure it only collects each
        email once.
        """
        test_emails = self.self_disti.collect_email_addresses()
        self.assertEqual(len(test_emails), 1)
        self.assertSetEqual(set([self.test1]), set(test_emails))

    def test_collect_distribution_with_cyclic_references(self):
        """
        Test that a distribution with cyclic references to ensure it only collects each
        email once.
        """
        test_emails = self.cyclic_disti1.collect_email_addresses()
        self.assertEqual(len(test_emails), 2)
        self.assertSetEqual(self.all_emails, set(test_emails))

        test_emails = self.cyclic_disti2.collect_email_addresses()
        self.assertEqual(len(test_emails), 2)
        self.assertSetEqual(self.all_emails, set(test_emails))


class RateLimitTestCase(TestCase):
    """
    Tests for the RateLimit model.
    """

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


class ServiceTestCase(TestCase):
    """
    Tests for the Service model.
    """

    def setUp(self):
        self.from_email = EmailAddress.objects.create(email_address="from@example.org")
        self.test1 = EmailAddress.objects.create(email_address="test1@example.org")
        self.test2 = EmailAddress.objects.create(email_address="test2@example.org")
        self.disti = Distribution.objects.create(name="Test Disti")
        self.disti.email_addresses.add(self.test1, self.test2)
        self.service = Service.objects.create(name="test_service")

    def test_constructor_properties(self):
        self.assertEqual(self.service.name, "test_service")
