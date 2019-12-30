"""
This module is for testing the templating feature.
"""

from django.test import TestCase

from ..models import Template


class TemplateTestCase(TestCase):
    def setUp(self):
        self.template = Template.objects.create(
            name="Test Template",
            subject="Test Subject",
            body_html="Test Body: {{ content }}",
            extends=None,
        )

    def test_constructor_properties(self):
        self.assertEqual(self.template.name, "Test Template")
        self.assertEqual(self.template.subject, "Test Subject")
        self.assertEqual(self.template.body_html, "Test Body: {{ content }}")
        self.assertIsNone(self.template.extends)
