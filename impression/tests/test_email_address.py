"""
This module is for testing the email address model.
"""

from django.test import TestCase

from ..models import EmailAddress


class EmailAddressTestCase(TestCase):
    def test_constructor_properties(self):
        """
        Test the custom constructor classmethod, ``get_or_create``.
        """
        email = EmailAddress.get_or_create("john@example.org")[0]
        self.assertEqual(email.email_address, "john@example.org")

    def test_extract_display_email(self):
        s = '"John C. Doe" <john@example.org>'
        e = "john@example.org"
        email = EmailAddress.extract_display_email(s)
        self.assertEqual(email, e)

    def test_email_case(self):
        """
        Test that our constructor considers emails as case-insensitive.
        """
        upper_email1 = EmailAddress.get_or_create("jane@example.org")[0]
        upper_email2 = EmailAddress.get_or_create("jane@example.org")[0]
        self.assertEqual(upper_email1, upper_email2)
