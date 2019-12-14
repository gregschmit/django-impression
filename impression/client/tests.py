"""
This module is for testing the email models, API, email backends, and template engine.
"""

from unittest import mock

from django.core.mail import send_mail
from django.core.mail.message import EmailMessage
from django.test import TestCase, override_settings

from .backends import RemoteEmailBackend
from .models import RemoteImpressionServer


class RemoteImpressionServerTestCase(TestCase):
    """
    Test RemoteImpressionServer model.
    """

    def setUp(self):
        self.remote_server = RemoteImpressionServer.objects.create(
            name="localhost",
            is_active=True,
            target="http://127.0.0.1:8000/api/send_message/",
            authentication_token="bad_secret_key",
        )

    def test_constructor_properties(self):
        self.assertEqual(self.remote_server.name, "localhost")


class RemoteEmailBackendTestCase(TestCase):
    """
    Test the remote email backend.
    """

    def setUp(self):
        self.remote_server = RemoteImpressionServer.objects.create(
            name="localhost",
            is_active=True,
            target="http://127.0.0.1:8000/api/send_message/",
            authentication_token="bad_key",
        )
        self.example_email = {
            "subject": "Test Subject",
            "body": "Test Body",
            "from_email": "testfrom@example.org",
            "to": ["test1@example.org", "test2@example.org"],
        }
        self.example_email2 = {
            "subject": "Test Subject 2",
            "body": "Test Body 2",
            "from_email": "testfrom@example.org",
            "to": ["test1@example.org", "test2@example.org"],
        }
        self.example_email_for_send_mail = {
            "subject": "Test Subject",
            "message": "Test Body",
            "from_email": "testfrom@example.org",
            "recipient_list": ["test1@example.org", "test2@example.org"],
        }

    @mock.patch("requests.post")
    def test_send_message(self, f):
        """
        Test sending a message raw via the backend.
        """
        backend = RemoteEmailBackend()
        message = EmailMessage(**self.example_email, connection=backend)
        backend.send_message(message)
        self.assertEqual(f.call_count, 1)
        call_args, call_kwargs = f.call_args_list[0]
        self.assertEqual(call_args[0], "http://127.0.0.1:8000/api/send_message/")
        self.assertEqual(call_kwargs["data"]["service_name"], "default")
        self.assertEqual(call_kwargs["data"]["subject"], "Test Subject")
        self.assertEqual(call_kwargs["data"]["body"], "Test Body")
        self.assertEqual(call_kwargs["data"]["from"], "testfrom@example.org")
        self.assertIn("test1@example.org", call_kwargs["data"]["to"])
        self.assertIn("test2@example.org", call_kwargs["data"]["to"])
        self.assertEqual(call_kwargs["headers"]["Authorization"], "Token bad_key")

    @mock.patch("requests.post")
    def test_send_messages(self, f):
        """
        Test sending multiple messages raw via the backend.
        """
        backend = RemoteEmailBackend()
        message1 = EmailMessage(**self.example_email, connection=backend)
        message2 = EmailMessage(**self.example_email2, connection=backend)
        backend.send_messages([message1, message2])
        self.assertEqual(f.call_count, 2)

        # test first message
        call_args, call_kwargs = f.call_args_list[0]
        self.assertEqual(call_args[0], "http://127.0.0.1:8000/api/send_message/")
        self.assertEqual(call_kwargs["data"]["service_name"], "default")
        self.assertEqual(call_kwargs["data"]["subject"], "Test Subject")
        self.assertEqual(call_kwargs["data"]["body"], "Test Body")
        self.assertEqual(call_kwargs["data"]["from"], "testfrom@example.org")
        self.assertIn("test1@example.org", call_kwargs["data"]["to"])
        self.assertIn("test2@example.org", call_kwargs["data"]["to"])
        self.assertEqual(call_kwargs["headers"]["Authorization"], "Token bad_key")

        # test second message
        call_args, call_kwargs = f.call_args_list[0]
        self.assertEqual(call_args[0], "http://127.0.0.1:8000/api/send_message/")
        self.assertEqual(call_kwargs["data"]["service_name"], "default")
        self.assertEqual(call_kwargs["data"]["subject"], "Test Subject")
        self.assertEqual(call_kwargs["data"]["body"], "Test Body")
        self.assertEqual(call_kwargs["data"]["from"], "testfrom@example.org")
        self.assertIn("test1@example.org", call_kwargs["data"]["to"])
        self.assertIn("test2@example.org", call_kwargs["data"]["to"])
        self.assertEqual(call_kwargs["headers"]["Authorization"], "Token bad_key")

    @mock.patch("requests.post")
    @override_settings(EMAIL_BACKEND="impression.client.backends.RemoteEmailBackend")
    def test_send_message_with_django(self, f):
        """
        Test sending email via Django using the proper setting.
        """
        send_mail(**self.example_email_for_send_mail)
        self.assertEqual(f.call_count, 1)
        call_args, call_kwargs = f.call_args_list[0]
        self.assertEqual(call_args[0], "http://127.0.0.1:8000/api/send_message/")
        self.assertEqual(call_kwargs["data"]["service_name"], "default")
        self.assertEqual(call_kwargs["data"]["subject"], "Test Subject")
        self.assertEqual(call_kwargs["data"]["body"], "Test Body")
        self.assertEqual(call_kwargs["data"]["from"], "testfrom@example.org")
        self.assertIn("test1@example.org", call_kwargs["data"]["to"])
        self.assertIn("test2@example.org", call_kwargs["data"]["to"])
        self.assertEqual(call_kwargs["headers"]["Authorization"], "Token bad_key")
