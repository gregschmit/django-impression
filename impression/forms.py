from django import forms

from .models import Template
from .widgets import AutogeneratePlainTextWidget, TemplateEditorWidget


class TemplateForm(forms.ModelForm):
    """
    Custom form to provide robust widgets for template editing.
    """

    class Meta:
        model = Template
        fields = (
            "name",
            "subject",
            "extends",
            "body_html",
            "autogenerate_plaintext_body",
            "body_plaintext",
        )
        widgets = {
            "body_html": TemplateEditorWidget,
            "autogenerate_plaintext_body": AutogeneratePlainTextWidget,
            "body_plaintext": TemplateEditorWidget,
        }
