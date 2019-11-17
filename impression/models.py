import json
import re

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage, get_connection
from django.core.validators import RegexValidator
from django.db import models
from django.template import Template as DjangoTemplate
from django.template.context import Context
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .settings import get_setting
from .template_engine import ImpressionTemplateEngine


class EmailAddress(models.Model):
    """
    Represents an email address and metadata about the email address.
    """

    email_address = models.EmailField(unique=True)
    service_unsubscriptions = models.ManyToManyField("impression.Service", blank=True)
    unsubscribed = models.BooleanField(
        default=False,
        help_text=_("Email is unsubscribed from everything."),
        db_index=True,
    )

    class Meta:
        verbose_name_plural = "Email addresses"

    def __str__(self):
        return self.email_address

    @classmethod
    def convert_emails(cls, emails):
        """
        Given a list of email strings, try to get an email object or create one, and
        ignore invalid emails, and return a list of the resulting email objects.
        """
        r = []
        for email in emails:
            try:
                r.append(cls.objects.get(email_address=email))
            except cls.DoesNotExist:
                e = cls(email_address=email)
                try:
                    e.full_clean()
                    e.save()
                    r.append(e)
                except ValidationError:
                    pass
        return r

    @staticmethod
    def extract_display_email(email):
        """
        If email might be in the format ``"Fred" <fred@example.com>``, then use this
        method to extract the real email. If the email is already in the raw format,
        then this method will still return the email address, unchanged.
        """
        email_re = re.compile(r".*<(.*)>")
        match = email_re.fullmatch(email)
        if match:
            return "".join(match.group(1).split())
        return "".join(email.split())


class DefaultTemplate:
    """
    A default template that simply renders the subject and body.
    """

    def render(self, context=None):
        """
        Render a template from just subject and body.
        """
        # build engine and evaluate/return
        engine = ImpressionTemplateEngine()
        return (
            DjangoTemplate("{{ subject }}", engine=engine).render(context),
            DjangoTemplate("{{ body }}", engine=engine).render(context),
        )


class Template(models.Model):
    """
    Represents an email template, written in the Django Template Language.
    """

    name_validator = RegexValidator(
        r"^[A-Za-z _-]+$",
        message=_("Name must only consist of letters, spaces, dashes, and underscores"),
        code="invalid_name_format",
    )
    name = models.CharField(max_length=255, unique=True, validators=[name_validator])
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    extends = models.ForeignKey(
        "self",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        help_text=_("Use this in place of the '{% extends %}' template tag."),
    )

    @property
    def help_text(self):
        return _(
            "Templates are written in the Django Template Language. For "
            "more information, see <a href={url}>{url}</a>.".format(
                url="https://docs.djangoproject.com/en/dev/ref/templates/language/"
            )
        )

    def __str__(self):
        return self.name

    def get_body(self):
        """
        Return the body, but with an ``{% extends %}`` tag injected if one is selected.
        """
        if self.extends:
            return '{{% extends "{}" %}}\n{}'.format(self.extends, self.body)
        return self.body

    def render(self, context={}):
        """
        Shortcut for rendering this template with a context. This will return a tuple in
        the form ``(subject, body)``.
        """
        # build engine and evaluate/return
        engine = ImpressionTemplateEngine()
        return (
            DjangoTemplate(self.subject, engine=engine).render(context),
            DjangoTemplate(self.get_body(), engine=engine).render(context),
        )


class Distribution(models.Model):
    """
    A collection of email addresses (and/or other distributions).
    """

    name = models.CharField(max_length=255, unique=True)
    email_addresses = models.ManyToManyField(EmailAddress, blank=True)
    distributions = models.ManyToManyField("self", symmetrical=False, blank=True)

    def collect_email_addresses(self, already_collected=None):
        """
        Collect emails and distributions, using the ``collect_distribution`` recursive
        method for distributions, and return a set of emails.
        """
        if not already_collected:
            already_collected = set([self])
        else:
            already_collected.add(self)
        r = set(self.email_addresses.all())
        for d in self.distributions.all():
            if not d in already_collected:
                r |= d.collect_email_addresses(already_collected)
        return r

    def __str__(self):
        return self.name


# class RateLimit(models.Model):
#     """
#     Represents a rate limit for sending emails to a service.
#     """


class Service(models.Model):
    """
    A combination of a template and email addresses/distributions that defines a target
    for an email request.
    """

    name_validator = RegexValidator(
        r"^[a-z0-9_]+$",
        message=_(
            "Name must only consist of lowercase letters, numbers, and underscores"
        ),
        code="invalid_name_format",
    )
    name = models.CharField(
        max_length=255,
        validators=[name_validator],
        unique=True,
        verbose_name="(URL Safe) Name",
        help_text=_(
            "Name must only contain lowercase letters, numbers, and underscores"
        ),
    )
    is_active = models.BooleanField(default=True, db_index=True)
    allowed_groups = models.ManyToManyField(
        Group,
        blank=True,
        help_text=_("Defines the groups who have access to the service."),
    )
    allow_override_email_from = models.BooleanField(
        default=False,
        help_text=_(
            "Whether users of the service are allowed to override the FROM email "
            "address of the service."
        ),
        verbose_name="Allow override of email FROM header",
    )
    allow_extra_target_email_addresses = models.BooleanField(
        default=False,
        help_text=_(
            "Whether we should accept extra email addresses in the TO/CC/BCC headers "
            "of the email message, or if we should ignore them and just use the "
            "service email configuration."
        ),
    )
    allow_json_body = models.BooleanField(
        default=True,
        help_text=_(
            "Try to decode the message body as a JSON and load into template context."
        ),
        verbose_name="Allow JSON body",
    )
    template = models.ForeignKey(
        Template, default=None, blank=True, null=True, on_delete=models.SET_NULL
    )
    from_email_address = models.ForeignKey(
        EmailAddress,
        blank=True,
        null=True,
        related_name="service_email_from_set",
        verbose_name="From",
        on_delete=models.SET_NULL,
        help_text=_("If blank, the 'DEFAULT_FROM_EMAIL' setting will be used."),
    )
    to_email_addresses = models.ManyToManyField(
        EmailAddress,
        blank=True,
        related_name="service_email_address_to_set",
        verbose_name="To",
    )
    to_distributions = models.ManyToManyField(
        Distribution,
        blank=True,
        related_name="service_distribution_to_set",
        verbose_name="To (distribution)",
    )
    cc_email_addresses = models.ManyToManyField(
        EmailAddress,
        blank=True,
        related_name="service_email_address_cc_set",
        verbose_name="CC",
    )
    cc_distributions = models.ManyToManyField(
        Distribution,
        blank=True,
        related_name="service_distribution_cc_set",
        verbose_name="CC (distribution)",
    )
    bcc_email_addresses = models.ManyToManyField(
        EmailAddress,
        blank=True,
        related_name="service_email_address_bcc_set",
        verbose_name="BCC",
    )
    bcc_distributions = models.ManyToManyField(
        Distribution,
        blank=True,
        related_name="service_distribution_bcc_set",
        verbose_name="BCC (distribution)",
    )

    def __str__(self):
        return self.name

    def collect_email_addresses(self):
        """
        Expand the distributions and return a tuple of sets (to, cc, bcc).
        """
        to = set(self.to_email_addresses.all())
        for d in self.to_distributions.all():
            to |= d.collect_email_addresses()
        cc = set(self.cc_email_addresses.all())
        for d in self.cc_distributions.all():
            cc |= d.collect_email_addresses()
        bcc = set(self.bcc_email_addresses.all())
        for d in self.bcc_distributions.all():
            bcc |= d.collect_email_addresses()
        return (to, cc, bcc)

    def get_template(self):
        """
        Return the template, or a default template object if one isn't assigned.
        """
        return self.template or DefaultTemplate()


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
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    override_from_email_address = models.ForeignKey(
        EmailAddress,
        blank=True,
        null=True,
        related_name="message_from_set",
        verbose_name="From (Override)",
        on_delete=models.SET_NULL,
    )
    extra_to_email_addresses = models.ManyToManyField(
        EmailAddress,
        blank=True,
        related_name="message_extra_to_set",
        verbose_name="Extra To",
    )
    extra_cc_email_addresses = models.ManyToManyField(
        EmailAddress,
        blank=True,
        related_name="message_extra_cc_set",
        verbose_name="Extra CC",
    )
    extra_bcc_email_addresses = models.ManyToManyField(
        EmailAddress,
        blank=True,
        related_name="message_extra_bcc_set",
        verbose_name="Extra BCC",
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    ready_to_send = models.BooleanField(default=False)
    sent = models.DateTimeField(default=None, blank=True, null=True)
    last_attempt = models.DateTimeField(default=None, blank=True, null=True)

    def __str__(self):
        return str(self.id)

    def save(self, *args, **kwargs):
        """
        Save the message. Then, if it looks ready to send, acquire DB lock, and send
        the message.
        """
        # save object first
        super().save(*args, **kwargs)

        # see if this object looks send-able; if so, send it
        if self.ready_to_send and not self.sent:
            self.send()

    def get_from_email(self):
        """
        Return either the service FROM email or the message FROM email, or the setting
        ``DEFAULT_FROM_EMAIL``, in that order, depending on whether the service allows
        the message to override the FROM email.
        """
        r = None
        if self.service.allow_override_email_from:
            r = self.override_from_email_address
        return r or self.service.from_email_address or get_setting("DEFAULT_FROM_EMAIL")

    def get_email_addresses(self):
        """
        Get the service emails, and add the message emails if permitted by the service.
        """
        (to, cc, bcc) = self.service.collect_email_addresses()
        if self.service.allow_extra_target_email_addresses:
            to |= set(self.extra_to_email_addresses.all())
            cc |= set(self.extra_cc_email_addresses.all())
            bcc |= set(self.extra_bcc_email_addresses.all())
        return (list(to), list(cc), list(bcc))

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
        from_email = self.get_from_email()
        to, cc, bcc = self.get_email_addresses()

        # build the message and send it
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=from_email,
            to=to,
            cc=cc,
            bcc=bcc,
            connection=connection,
        )
        self.last_attempt = timezone.now()
        if email.send():
            self.sent = timezone.now()

        self.save()
