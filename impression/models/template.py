from django.core.validators import RegexValidator
from django.db import models
from django.template import Template as DjangoTemplate
from django.utils.translation import gettext_lazy as _

from ..template_engine import ImpressionTemplateEngine


class DefaultTemplate:
    """
    A default template that simply renders the subject and body.
    """

    def render(self, context=None):
        """
        Render a template from just subject and body.
        """
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
    subject = models.CharField(max_length=255, blank=True, default="{{ subject }}")
    body = models.TextField(blank=True, default="{{ body }}")
    extends = models.ForeignKey(
        "self",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        help_text=_("Use this in place of the '{% extends %}' template tag."),
    )

    help_text = _(
        "Templates are written in the Django Template Language. For more information, "
        "see <a href={url}>{url}</a>.".format(
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
        engine = ImpressionTemplateEngine()
        return (
            DjangoTemplate(self.subject, engine=engine).render(context),
            DjangoTemplate(self.get_body(), engine=engine).render(context),
        )
