from django.contrib.auth.models import Group
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from ..settings import get_setting


class ServiceQuerySet(models.QuerySet):
    def get_by_natural_key(self, name):
        return self.get(name=name)


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
        verbose_name=_("Name (URL Safe)"),
        help_text=_(
            "Name must only contain lowercase letters, numbers, and underscores"
        ),
    )
    is_active = models.BooleanField(default=True, db_index=True)
    is_unsubscribable = models.BooleanField(
        default=True,
        help_text=_(
            "Disabling this option will send emails to users even if they are "
            "unsubscribed to this service. You should only use this for emails which "
            "are not periodic. A good example might be a service for order "
            "confirmations, where the concept of 'unsubscribing' to those emails is "
            "not sensible."
        ),
    )
    allowed_groups = models.ManyToManyField(
        Group,
        blank=True,
        help_text=_("Defines the groups who have access to the service."),
    )
    rate_limit = models.ForeignKey(
        "impression.RateLimit", blank=True, null=True, on_delete=models.SET_NULL
    )
    allow_override_email_from = models.BooleanField(
        default=False,
        help_text=_(
            "Whether users of the service are allowed to override the FROM email "
            "address of the service."
        ),
        verbose_name=_("Allow override of email FROM header"),
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
        verbose_name=_("Allow JSON body"),
    )
    template = models.ForeignKey(
        "impression.Template", blank=True, null=True, on_delete=models.SET_NULL
    )
    from_email_address = models.ForeignKey(
        "impression.EmailAddress",
        blank=True,
        null=True,
        related_name="service_email_from_set",
        verbose_name=_("From"),
        on_delete=models.SET_NULL,
        help_text=_("If blank, the 'DEFAULT_FROM_EMAIL' setting will be used."),
    )
    to_email_addresses = models.ManyToManyField(
        "impression.EmailAddress",
        blank=True,
        related_name="service_email_address_to_set",
        verbose_name=_("To"),
    )
    to_distributions = models.ManyToManyField(
        "impression.Distribution",
        blank=True,
        related_name="service_distribution_to_set",
        verbose_name=_("To (distribution)"),
    )
    cc_email_addresses = models.ManyToManyField(
        "impression.EmailAddress",
        blank=True,
        related_name="service_email_address_cc_set",
        verbose_name=_("CC"),
    )
    cc_distributions = models.ManyToManyField(
        "impression.Distribution",
        blank=True,
        related_name="service_distribution_cc_set",
        verbose_name=_("CC (distribution)"),
    )
    bcc_email_addresses = models.ManyToManyField(
        "impression.EmailAddress",
        blank=True,
        related_name="service_email_address_bcc_set",
        verbose_name=_("BCC"),
    )
    bcc_distributions = models.ManyToManyField(
        "impression.Distribution",
        blank=True,
        related_name="service_distribution_bcc_set",
        verbose_name=_("BCC (distribution)"),
    )

    objects = ServiceQuerySet.as_manager()

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)

    def collect_email_addresses(self):
        """
        Expand the distributions and return a tuple of sets (to, cc, bcc).
        """
        return (
            collect_email_addresses_by_kind("to"),
            collect_email_addresses_by_kind("cc"),
            collect_email_addresses_by_kind("bcc"),
        )

    def collect_email_addresses_by_kind(self, kind="to"):
        """
        Expand the distributions and return a set of emails, given a `kind` which should
        be one of: "to", "cc", or "bcc".
        """
        s = set(getattr(self, "{}_email_addresses".format(kind)).all())
        for d in getattr(self, "{}_distributions".format(kind)).all():
            s |= d.collect_email_addresses()
        return s

    def get_from_email(self, override_email=None):
        """
        Return the `override_email` if this service permits, otherwise the
        `default_from_email` or as a last resort, the settings `DEFAULT_FROM_EMAIL`.
        """
        # override the email if permitted
        if override_email and self.allow_override_email_from:
            if isinstance(override_email, EmailAddress):
                return override_email
            return EmailAddress.get_or_create(override_email)[0]

        # use the service default
        if self.default_from_email:
            return self.default_from_email

        # last resort, use the DEFAULT_FROM_EMAIL
        return EmailAddress.get_or_create(get_setting("DEFAULT_FROM_EMAIL"))[0]

    def get_template(self):
        """
        Return the template, or a default template object if one isn't assigned.
        """
        return self.template or DefaultTemplate()

    def check_rate_limit(self, user=None, groups=None):
        """
        Check whether the rate limit has been reach by this user or by any of the
        relevant groups. If no rate limit is provided, return True.
        """
        if not self.rate_limit:
            return True
        return self.rate_limit.check_service(self, user, groups)

    def filter_unsubscribed(self, emails):
        """
        Filter out emails which are unsubscribed.
        """
        if self.is_unsubscribable:
            return [e for e in emails if not e.is_unsubscribed_from(self)]
        return emails
