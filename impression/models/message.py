import json

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.mail import EmailMultiAlternatives, get_connection
from django.db import models
from django.template.context import Context
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .email_address import EmailAddress
from ..exceptions import RateLimitException, JSONBodyRequired
from ..settings import get_setting


class Message(models.Model):
    """
    Represents an email message assigned to a service.
    """

    service = models.ForeignKey(
        "impression.Service", on_delete=models.CASCADE, related_name="messages"
    )
    user_type = models.ForeignKey(
        ContentType,
        blank=True,
        null=True,
        default=None,
        on_delete=models.SET_NULL,
        help_text=_("The type of the user that this message is associated with."),
    )
    user_id = models.PositiveIntegerField(
        _("User ID"),
        blank=True,
        null=True,
        default=None,
        help_text=_("The ID of the user that this message is associated with."),
    )
    user = GenericForeignKey("user_type", "user_id")

    # core message content
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField(
        blank=True,
        help_text=_(
            "This can be a JSON string to pass arguments to the service, if the service"
            " allows."
        ),
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

    # meta-data properties
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    ready_to_send = models.BooleanField(default=False)
    sent = models.DateTimeField(blank=True, null=True)
    last_attempt = models.DateTimeField(blank=True, null=True)

    # meta-data for after the message is sent
    final_subject = models.TextField(_("Subject (final)"), blank=True, editable=False)
    final_body_plaintext = models.TextField(
        _("Body (plaintext, final)"), blank=True, editable=False
    )
    final_body_html = models.TextField(
        _("Body (HTML, final)"), blank=True, editable=False
    )
    final_from_email_address = models.ForeignKey(
        "impression.EmailAddress",
        blank=True,
        null=True,
        related_name="message_final_from_set",
        verbose_name=_("From (final)"),
        on_delete=models.SET_NULL,
        editable=False,
    )
    final_to_email_addresses = models.ManyToManyField(
        "impression.EmailAddress",
        blank=True,
        related_name="message_final_to_set",
        verbose_name=_("To (final)"),
        editable=False,
    )
    final_cc_email_addresses = models.ManyToManyField(
        "impression.EmailAddress",
        blank=True,
        related_name="message_final_cc_set",
        verbose_name=_("CC (final)"),
        editable=False,
    )
    final_bcc_email_addresses = models.ManyToManyField(
        "impression.EmailAddress",
        blank=True,
        related_name="message_final_bcc_set",
        verbose_name=_("BCC (final)"),
        editable=False,
    )

    ready_query = models.Q(ready_to_send=True, send__isnull=True)

    def __str__(self):
        return str(self.id)

    def _pre_create_check(self):
        """
        Checks to be done before message is created. Raise exceptions for errors.
        """
        # check if we hit our rate limit
        if self.service.rate_limit:
            groups = (
                self.user.groups.all() & self.service.allowed_groups.all()
                if self.user
                else None
            )
            if not self.service.check_rate_limit(self.user, groups):
                raise RateLimitException()

        # check if the body passes the json_body_policy
        if self.service.json_body_policy in [self.service.FORBID, self.service.PERMIT]:
            pass
        elif self.service.json_body_policy == self.service.REQUIRE:
            body = {}
            try:
                body.update(json.loads(self.body))
            except (json.JSONDecodeError, TypeError):  # body is not a JSON object
                raise JSONBodyRequired()
        else:
            raise ValueError(
                "json_body_policy is not valid (bad value {} for obj {})".format(
                    self.service.json_body_policy, self.service.pk
                )
            )

    def save(self, *args, **kwargs):
        """
        Save the message. Then, if it looks ready to send but sending hasn't been
        attempted, acquire DB lock, and send the message.

        For messages being created (pk=None), there are initial checks for things like
        rate limiting and body content validity.
        """
        # checks before Message is created
        if self.pk is None:
            self._pre_create_check()

        # save object first
        super().save(*args, **kwargs)

        # see if we are send-able and we haven't yet attempted; if so, send it
        if self.ready_to_send and not self.sent and not self.last_attempt:
            self.send()

    def get_user_display(self):
        """
        Get a string representation of the `user` generic foreign key.
        """
        if not self.user:
            return ""
        return "{} ({}, {})".format(self.user, self.user_type, self.user_id)

    def get_from_email(self):
        """
        Return the proper "FROM" EmailAddress object. If the service allows the message
        to override the FROM email, then use the `override_from_email_address`,
        otherwise use the service's `from_email_address`, or if that is None, use the
        setting `DEFAULT_FROM_EMAIL`
        """
        # override the email if permitted
        if self.override_from_email_address and self.service.allow_override_email_from:
            return self.override_from_email_address

        # use the service default
        if self.service.from_email_address:
            return self.service.from_email_address

        # last resort, use the DEFAULT_FROM_EMAIL
        return EmailAddress.get_or_create(get_setting("DEFAULT_FROM_EMAIL"))[0]

    def _get_final_emails_by_kind(self, initial_set, kind="to"):
        """
        Intersect the initial_set with the extra emails on this message (per the kind),
        and then filter the unsubscribed emails.

        Return a set of EmailAddress objects.
        """
        return self.service.filter_unsubscribed(
            initial_set
            | set(getattr(self, "extra_{}_email_addresses".format(kind)).all())
        )

    def get_final_emails(self):
        """
        Collect the union of emails from this message and the service, and ensure
        that unsubscribed emails are filtered out.

        Return a tuple of sets of EmailAddress objects in the form (to, cc, bcc).
        """
        to, cc, bcc = self.service.collect_email_addresses()
        return (
            self._get_final_emails_by_kind(to, "to"),
            self._get_final_emails_by_kind(cc, "cc"),
            self._get_final_emails_by_kind(bcc, "bcc"),
        )

    def get_context(self):
        """
        Get the Context object for this message. Try to decode the body as a JSON and
        load into context if ``self.service.allow_json_body`` is ``True``.
        """
        context = Context()
        context["subject"] = self.subject
        context["body"] = self.body
        if self.service.json_body_policy in [self.service.PERMIT, self.service.REQUIRE]:
            try:
                context.update(json.loads(self.body))
            except json.JSONDecodeError:  # body is not a JSON
                pass
            except TypeError:  # top level JSON is not an object
                pass
        elif self.service.json_body_policy == self.service.FORBID:
            pass  # do not attempt to load body as JSON into context
        else:
            raise ValueError(
                "json_body_policy is not valid (bad value {} for obj {})".format(
                    self.service.json_body_policy, self.service.pk
                )
            )
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
        subject, plaintext_body, html_body = self.render()

        # build the email message
        to, cc, bcc = self.get_final_emails()
        from_email = self.get_from_email()
        email = EmailMultiAlternatives(
            subject=subject,
            body=plaintext_body,
            from_email=from_email,
            to=[e.email_address for e in to],
            cc=[e.email_address for e in cc],
            bcc=[e.email_address for e in bcc],
            connection=connection,
        )
        if html_body:
            email.attach_alternative(html_body, "text/html")

        # send the message
        self.last_attempt = timezone.now()
        if email.send():
            self.sent = timezone.now()

            # store the final sent message details
            self.final_from_email_address = from_email
            self.final_to_email_addresses.add(*to)
            self.final_cc_email_addresses.add(*cc)
            self.final_bcc_email_addresses.add(*bcc)
            self.final_subject = subject
            self.final_body_plaintext = plaintext_body or ""
            self.final_body_html = html_body or ""

        self.save()
