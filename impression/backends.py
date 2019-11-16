"""
This module implements our local email backend.
"""

import requests

from django.core.mail.backends.base import BaseEmailBackend

from .models import EmailAddress, Message, Service
from .settings import get_setting


class LocalEmailBackend(BaseEmailBackend):
    """
    This backend adds emails to the ``impression.models.Message`` model. We respect the
    from/to/cc/bcc fields here to allow this backend to be a drop-in replacement for
    whatever their true sending backend is.
    """

    def send_message(self, message):
        """
        Add a single email message to the ``impression.models.Email`` model and return
        the resulting object.
        """
        # extract FROM email
        if message.from_email:
            from_email, _ = EmailAddress.objects.get_or_create(
                email_address=EmailAddress.extract_display_email(message.from_email)
            )
        else:
            from_email = None

        # determine if we should interpret the first address in "to" as the service
        if message.to and not "@" in message.to[0]:
            service_name = message.to[0]
            to_emails = message.to[1:]
        else:
            service_name = get_setting("IMPRESSION_DEFAULT_SERVICE")
            to_emails = message.to

        # parse emails and build message
        to_l = EmailAddress.convert_emails(to_emails or [])
        cc_l = EmailAddress.convert_emails(message.cc or [])
        bcc_l = EmailAddress.convert_emails(message.bcc or [])
        m = Message(
            service=Service.objects.get(name=service_name),
            override_from_email_address=from_email,
            subject=message.subject,
            body=message.body,
        )
        m.save()
        m.extra_to_email_addresses.add(*to_l)
        m.extra_cc_email_addresses.add(*cc_l)
        m.extra_bcc_email_addresses.add(*bcc_l)

        # signal message can be sent
        m.ready_to_send = True
        m.save()

        return m

    def send_messages(self, email_messages):
        """
        Call ``send_message()`` for each email message, and return the number which were
        successfully processed.
        """
        successful = []
        for e in email_messages:
            m = self.send_message(e)
            if m:
                successful.append(m)
        return len(successful)
