"""
This module is for testing services.
"""

from django.test import TestCase

from ..models import EmailAddress, Distribution, Service


class ServiceTestCase(TestCase):
    def setUp(self):
        self.from_email = EmailAddress.objects.create(email_address="from@example.org")
        self.test1 = EmailAddress.objects.create(email_address="test1@example.org")
        self.test2 = EmailAddress.objects.create(email_address="test2@example.org")
        self.disti = Distribution.objects.create(name="Test Disti")
        self.disti.email_addresses.add(self.test1, self.test2)
        self.service = Service.objects.create(name="test_service")

    def test_constructor_properties(self):
        self.assertEqual(self.service.name, "test_service")
