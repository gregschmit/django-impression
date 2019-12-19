from copy import copy
from django.contrib import admin

from .. import __version__


class CustomAdminSite(admin.AdminSite):
    """
    Provide an optional custom admin site for Impression.
    """

    site_title = site_header = "Impression"
    index_title = "Home"

    def __init__(self, *args, **kwargs):
        """
        This method should copy over the configurations from Django's admin site. We do
        this here to avoid each app having to register with this custom site. Ensure
        that (contrary to Django docs) you keep the original ``django.contrib.admin``
        in the ``INSTALLED_APPS``.
        """
        super().__init__(*args, **kwargs)
        for model, model_admin in admin.site._registry.items():
            new_model_admin = copy(model_admin)
            new_model_admin.admin_site = self
            self._registry[model] = new_model_admin

    def each_context(self, request):
        """
        Load the version into the template context.
        """
        context = super().each_context(request)
        context["version"] = __version__
        return context


custom_admin_site = CustomAdminSite(name="admin")
