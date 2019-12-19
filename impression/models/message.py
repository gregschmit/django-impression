import json

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.mail import EmailMessage, get_connection
from django.db import models
from django.utils.translation import gettext_lazy as _

from .email_address import EmailAddress
from ..settings import get_setting


class Message(models.Model):
    """
    Represents an email message assigned to a service.
    """

    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField(
        blank=True,
        help_text=_(
            "This can be either a single string, or an encoded JSON to pass arguments "
            "to the service."
        ),
    )
    user_type = models.ForeignKey(
        ContentType,
        blank=True,
        null=True,
        default=None,
        on_delete=models.SET_NULL,
        help_text=_("The user model that this message is associated with."),
    )
    user_id = models.PositiveIntegerField(
        _("User ID"), blank=True, null=True, default=None
    )
    user = GenericForeignKey("user_type", "user_id")
    service = models.ForeignKey(
        "impression.Service", on_delete=models.CASCADE, related_name="messages"
    )
    override_from_email_address = models.ForeignKey(
        "impression.EmailAddress",
        blank=True,
        null=True,
        related_name="message_override_from_set",
        verbose_name=_("From (Override)"),
        on_delete=models.SET_NULL,
    )
    extra_to_email_addresses = models.ManyToManyField(
        "impression.EmailAddress",
        blank=True,
        related_name="message_extra_to_set",
        verbose_name=_("Extra To"),
    )
    extra_cc_email_addresses = models.ManyToManyField(
        "impression.EmailAddress",
        blank=True,
        related_name="message_extra_cc_set",
        verbose_name=_("Extra CC"),
    )
    extra_bcc_email_addresses = models.ManyToManyField(
        "impression.EmailAddress",
        blank=True,
        related_name="message_extra_bcc_set",
        verbose_name=_("Extra BCC"),
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    ready_to_send = models.BooleanField(default=False)
    sent = models.DateTimeField(blank=True, null=True)
    last_attempt = models.DateTimeField(blank=True, null=True)

    # final meta attributes (saved when message is sent)
    final_from_email_address = models.ForeignKey(
        "impression.EmailAddress",
        blank=True,
        null=True,
        related_name="message_final_from_set",
        verbose_name=_("From (Final)"),
        on_delete=models.SET_NULL,
        editable=False,
    )
    final_to_email_addresses = models.ManyToManyField(
        "impression.EmailAddress",
        blank=True,
        related_name="message_final_to_set",
        verbose_name=_("Final To"),
        editable=False,
    )
    final_cc_email_addresses = models.ManyToManyField(
        "impression.EmailAddress",
        blank=True,
        related_name="message_final_cc_set",
        verbose_name=_("Final CC"),
        editable=False,
    )
    final_bcc_email_addresses = models.ManyToManyField(
        "impression.EmailAddress",
        blank=True,
        related_name="message_final_bcc_set",
        verbose_name=_("Final BCC"),
        editable=False,
    )
    final_subject = models.TextField(blank=True, editable=False)
    final_body = models.TextField(blank=True, editable=False)

    def __str__(self):
        return str(self.id)

    def save(self, *args, **kwargs):
        """
        Save the message. Then, if it looks ready to send but sending hasn't been
        attempted, acquire DB lock, and send the message.
        """
        # check if we hit our rate limit
        if self.pk is None and self.service.rate_limit:
            groups = (
                self.user.groups.all() & self.service.allowed_groups.all()
                if self.user
                else None
            )
            if not self.service.check_rate_limit(self.user, groups):
                raise RateLimitException()

        # save object first
        super().save(*args, **kwargs)

        # see if we are send-able and we haven't yet attempted; if so, send it
        if self.ready_to_send and not self.sent and not self.last_attempt:
            self.send()

    def get_final_emails(self, kind="to"):
        """
        Collect the union of emails from this message and the service, and ensure
        that unsubscribed emails are filtered out.

        Return an iterable of email address strings.
        """
        final_set = self.service.collect_email_addresses_by_kind(kind)
        final_set |= set(
            [
                EmailAddress.get_or_create(e)[0]
                for e in getattr(self, "extra_{}_email_addresses".format(kind))
            ]
        )
        return [e.email_address for e in self.service.filter_unsubscribed(final_set)]

    def get_context(self):
        """
        Get the Context object for this message. Try to decode the body as a JSON and
        load into context if ``self.service.allow_json_body`` is ``True``.
        """
        context = Context()
        context["subject"] = self.subject
        context["body"] = self.body
        if self.service.allow_json_body:
            try:
                context.update(json.loads(self.body))
            except json.JSONDecodeError:  # body is not a JSON
                pass
            except TypeError:  # result is not a dict
                pass
        return context

    def render(self):
        """
        Render this message using the service template.
        """
        return self.service.get_template().render(self.get_context())

    def send(self):
        """
        Send the message via the "real" email backend.
        """

        # get the "real" backend/connection
        backend = get_setting("IMPRESSION_EMAIL_BACKEND")
        connection = get_connection(backend)

        # compile the message using the template, extract other properties
        subject, body = self.render()

        # build the email message
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=self.override_from_email_address,
            to=self.extra_to_email_addresses.all(),
            cc=self.extra_cc_email_addresses.all(),
            bcc=self.extra_bcc_email_addresses.all(),
            connection=connection,
        )

        # send the message
        self.last_attempt = timezone.now()
        if email.send():
            self.sent = timezone.now()

            # store the final message details

        self.save()
