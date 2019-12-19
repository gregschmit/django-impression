"""
This module implements our remote email backend.
"""

import requests

from django.core.mail.backends.base import BaseEmailBackend

from ..settings import get_setting


class RemoteEmailBackend(BaseEmailBackend):
    """
    This backend sends a RESTful request to the target Impression server, and allows
    that remote installation of Impression to send the email(s). This backend will send
    the remote server the raw from/to/cc/bcc fields, however it's up to the remote
    service if it will trust you enough to use these fields.
    """

    @staticmethod
    def send_message(message):
        """
        Send a RESTful request to the target impression server and return the response.
        """
        # get target/token
        try:
            from .models import RemoteImpressionServer

            target, token = RemoteImpressionServer.get_target_and_token()
        except RuntimeError:
            target = get_setting("IMPRESSION_DEFAULT_TARGET")
            token = get_setting("IMPRESSION_DEFAULT_TOKEN")

        # build headers
        headers = {"Authorization": "Token {}".format(token)}

        # determine if we should interpret the first address in "to" as the service
        if message.to and not "@" in message.to[0]:
            service_name = message.to[0]
            to_emails = message.to[1:]
        else:
            service_name = get_setting("IMPRESSION_DEFAULT_SERVICE")
            to_emails = message.to

        # send the request
        payload = {
            "service_name": service_name,
            "subject": message.subject,
            "body": message.body,
            "from": message.from_email,
            "to": to_emails or [],
        }
        if message.cc:
            payload["cc"] = message.cc
        if message.bcc:
            payload["bcc"] = message.bcc
        return requests.post(target, data=payload, headers=headers)

    def send_messages(self, email_messages):
        """
        For each email message, send RESTful request to the remote server and return the
        number which returned non-error response codes.
        """
        count = 0
        for msg in email_messages:
            response = self.send_message(msg)
            print(response.text)
            count += response.ok
        return count
