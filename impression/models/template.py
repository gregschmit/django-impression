from bs4 import BeautifulSoup

from django.core.validators import RegexValidator
from django.db import models
from django.template import Template as DjangoTemplate
from django.utils.translation import gettext_lazy as _

from ..template_engine import ImpressionTemplateEngine


class DefaultTemplate:
    """
    A simple default template that renders the subject and body, only in plaintext.
    """

    def render(self, context=None):
        """
        Render a template from just subject and body.
        """
        if context is None:
            context = {}
        engine = ImpressionTemplateEngine()
        return (
            DjangoTemplate("{{ subject }}", engine=engine).render(context),
            DjangoTemplate("{{ body }}", engine=engine).render(context),
            None,
        )


class TemplateQuerySet(models.QuerySet):
    def get_by_natural_key(self, name):
        return self.get(name=name)


default_html_email = """<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
</head>
<body>
  <div>{{ body }}</div>
</body>
</html>
"""


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
    extends = models.ForeignKey(
        "self",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        help_text=_("Use this in place of the '{% extends %}' template tag."),
    )
    subject = models.CharField(max_length=255, blank=True, default="{{ subject }}")
    body_html = models.TextField(
        _("Body (HTML)"), blank=True, default=default_html_email
    )
    autogenerate_plaintext_body = models.BooleanField(
        _("Autogenerate plaintext body"),
        default=True,
        help_text=_(
            "If this option is selected, then the plaintext body will be dynamically "
            "generated from the HTML body."
        ),
    )
    body_plaintext = models.TextField(
        _("Body (plaintext)"), blank=True, default="{{ body }}"
    )

    help_text = _(
        "Templates are written in the Django Template Language. For more information, "
        "see <a href={url}>{url}</a>.".format(
            url="https://docs.djangoproject.com/en/dev/ref/templates/language/"
        )
    )

    objects = TemplateQuerySet.as_manager()
    _ext = '{{% extends "{}{{{}}}" %}}\n{}'

    def __str__(self):
        return self.name

    def get_body_html(self):
        """
        Helper for getting the HTML body, including the ``extends`` tag, if needed.
        """
        if self.extends:
            return self._ext.format(self.extends, "html", self.body_html)
        return self.body_html

    def get_body_plaintext(self):
        """
        Helper for getting the HTML body, including the ``extends`` tag, if needed. If
        ``autogenerate_plaintext_body`` is True, return the cleaned HTML body.
        """
        if self.autogenerate_plaintext_body:
            if self.extends:
                body_html = self._ext.format(self.extends, "plaintext", self.body_html)
            else:
                body_html = self.body_html
            return BeautifulSoup(body_html).get_text().strip()
        if self.extends:
            return self._ext.format(self.extends, "plaintext", self.body_plaintext)
        return self.body_plaintext

    def render(self, context=None):
        """
        Render this template with a context. Return a tuple in the form ``(subject,
        plaintext_body, html_body)``.
        """
        if context is None:
            context = {}
        engine = ImpressionTemplateEngine()

        # return a tuple of the compiled templates for subject and body
        return (
            DjangoTemplate(self.subject, engine=engine).render(context),
            DjangoTemplate(self.get_body_plaintext(), engine=engine).render(context),
            DjangoTemplate(self.get_body_html(), engine=engine).render(context),
        )
