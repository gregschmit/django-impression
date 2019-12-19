import re

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from ..settings import get_setting


class EmailAddressQuerySet(models.QuerySet):
    def get_by_natural_key(self, email_address):
        return self.get(email_address=email_address)


class EmailAddress(models.Model):
    """
    Represents an email address and metadata about the email address.
    """

    email_address = models.EmailField(unique=True)
    service_unsubscriptions = models.ManyToManyField("impression.Service", blank=True)
    unsubscribed_from_all = models.BooleanField(
        default=False,
        help_text=_("Email is unsubscribed from everything."),
        db_index=True,
    )

    objects = EmailAddressQuerySet.as_manager()

    class Meta:
        verbose_name_plural = "Email addresses"

    def __str__(self):
        return self.email_address

    def natural_key(self):
        return (self.email_address,)

    def clean(self):
        # lowercase the email address
        self.email_address = self.email_address.lower()

    def is_unsubscribed_from(self, service):
        """
        This is a helper method that returns whether a user is unsubscribed from a
        particular service, or ``True`` for all services if this user is unsubscribed
        from everything.
        """
        return self.unsubscribed_from_all or (
            service in self.service_unsubscriptions.all()
        )

    @classmethod
    def convert_emails(cls, emails):
        """
        Given a list of email strings, try to get an email object or create one, and
        ignore invalid emails, and return a list of the resulting email objects.
        """
        email_list = []
        for email in emails:
            try:
                email_list.append(cls.get_or_create(email)[0])
            except ValidationError:
                pass
        return email_list

    @classmethod
    def get_or_create(cls, email_string):
        """
        Given an email string, try to convert it to an email object.
        """
        # allow for email format variants
        email_string = cls.extract_display_email(email_string)

        # try to create EmailAddress
        try:
            email = cls.objects.get(email_address=email_string)
            created = False
        except cls.DoesNotExist:
            email = cls(email_address=email_string)
            created = True

        # full clean if created
        if created:
            email.full_clean()
            # set unsubscribe if IMPRESSION_DEFAULT_UNSUBSCRIBED
            if get_setting("IMPRESSION_DEFAULT_UNSUBSCRIBED"):
                email.unsubscribed_from_all = True
            email.save()
        return email, created

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
            return "".join(match.group(1).split()).lower()
        return "".join(email.split()).lower()
