"""
This module provides a template engine that is configured to first load templates from
the Template model.
"""

import re

from django.apps import apps
from django.template.base import Origin, Template as DjangoTemplate
from django.template.engine import Engine
from django.template.loaders.base import Loader


class ImpressionTemplateLoader(Loader):
    """
    A template loader that pulls templates from the database. Template names should have
    either "{html}" or "{plaintext}" appended to specify which template body should be
    used.
    """

    name_pattern = re.compile(r"^(.*)\{([a-z]+)\}$")

    def get_template_body(self, template, body_type):
        """
        Extract the body (template) depending on the ``body_type``.
        """
        if body_type == "html":
            return template.get_body_html()
        elif body_type == "plaintext":
            return template.get_body_plaintext()
        raise ValueError('body_type should be one of "html" or "plaintext"')

    def get_template(self, template_name, *args, **kwargs):
        """
        Return the template with the given name. The template_name should have the type
        (``{html}`` or ``{plaintext}``) appended to the template model instance name.
        """
        # use get_model because models.py imports this module - avoid cyclic imports
        template_model = apps.get_model("impression", "Template")
        match = self.name_pattern.match(template_name)
        if not match:
            raise ValueError(
                'template_name must end with either "{html}" or "{plaintext}"'
            )
        template_shortname = match[1]
        body_type = match[2]
        template = template_model.objects.get(name=template_shortname)
        origin = Origin(
            name="Impression Model Template",
            template_name=template_name,
            loader=type(self).__name__,
        )
        return DjangoTemplate(
            self.get_template_body(template, body_type), origin=origin,
        )

    def get_template_sources(self, template_name):
        pass


class ImpressionTemplateEngine(Engine):
    """
    Inject the model template loader.
    """

    def __init__(self, *args, **kwargs):
        """
        Inject the custom template loader.
        """
        super().__init__(*args, **kwargs)
        if not self.loaders:
            self.loaders = []
        self.loaders = [
            "impression.template_engine.ImpressionTemplateLoader",
            *self.loaders,
        ]
