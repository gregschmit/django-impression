"""
This module provides a template engine that is configured to first load templates from
the Template model.
"""

from django.apps import apps
from django.template.base import Origin, Template as DjangoTemplate
from django.template.engine import Engine
from django.template.loaders.base import Loader


class ImpressionTemplateLoader(Loader):
    """
    A template loader that pulls templates from the database.
    """

    def get_template(self, template_name, *args, **kwargs):
        """
        Return the template with the given name, without catching exceptions.
        """
        # use get_model because models.py imports this module - avoid cyclic imports
        template_model = apps.get_model("impression", "Template")

        template = template_model.objects.get(name=template_name)
        origin = Origin(
            name="Impression Model Template",
            template_name=template_name,
            loader=type(self).__name__,
        )
        return DjangoTemplate(template.get_body(), origin=origin)

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
            "impression.email.template_engine.ImpressionTemplateLoader",
            *self.loaders,
        ]
