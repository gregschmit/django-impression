from django import forms
from django.templatetags.static import static


class BaseEditorWidget(forms.Textarea):
    class Media:
        """
        Include JavaScripts and CSS here for CodeMirror, Django, and themes.
        """

        css = {
            "all": [
                "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.48.4/codemirror.min.css",
                "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.48.4/theme/base16-light.min.css",
                "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.48.4/theme/base16-dark.min.css",
                "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.48.4/theme/solarized.min.css",
            ]
        }
        js = [
            # base
            "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.48.4/codemirror.min.js",
            "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.48.4/addon/mode/overlay.min.js",
            # languages
            "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.48.4/mode/xml/xml.min.js",
            "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.48.4/mode/htmlmixed/htmlmixed.min.js",
            "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.48.4/mode/django/django.min.js",
            "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.48.4/mode/css/css.min.js",
            "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.48.4/mode/sass/sass.min.js",
            "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.48.4/mode/javascript/javascript.min.js",
        ]


class TemplateEditorWidget(BaseEditorWidget):
    def __init__(self, *args, **kwargs):
        r = super().__init__(*args, **kwargs)

        # add class to flag this widget as an editor
        self.attrs["class"] = "impression-template-editor"

        # append javascript init file
        self.Media.js.append(static("impression/js/codemirror-init.js"))

        return r
