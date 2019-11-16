from django.contrib import admin
from django.db.models import TextField
from django.utils.translation import gettext_lazy as _

from . import models
from .widgets import TemplateEditorWidget


@admin.register(models.EmailAddress)
class EmailAddressAdmin(admin.ModelAdmin):
    list_filter = ("unsubscribed",)
    search_fields = ("email_address",)
    list_display = ("email_address", "unsubscribed")


@admin.register(models.Template)
class TemplateAdmin(admin.ModelAdmin):
    list_filter = ("extends",)
    search_fields = ("subject", "body", "extends")
    list_display = ("name", "subject", "extends")
    formfield_overrides = {TextField: {"widget": TemplateEditorWidget}}


@admin.register(models.Distribution)
class DistributionAdmin(admin.ModelAdmin):
    search_fields = list_display = ("name",)


@admin.register(models.Service)
class ServiceAdmin(admin.ModelAdmin):
    list_filter = ("is_active", "allow_json_body", "template", "from_email_address")
    search_fields = ("name",)
    list_display = (
        "name",
        "is_active",
        "allow_json_body",
        "template",
        "from_email_address",
    )


class EmailMessageSentFilter(admin.SimpleListFilter):
    """
    A filter to only show unsent/sent messages.
    """

    title = _("email sent")
    parameter_name = "email_sent"

    def lookups(self, request, model_admin):
        """
        Return a tuple of the filter options.
        """
        return (("sent", _("Sent")), ("unsent", _("Unsent")))

    def queryset(self, request, queryset):
        """
        Return the filtered queryset based on the filter value.
        """
        v = self.value()
        if v == "sent":
            return queryset.filter(sent__isnull=False)
        elif v == "unsent":
            return queryset.filter(sent__isnull=True)
        return queryset


@admin.register(models.Message)
class MessageAdmin(admin.ModelAdmin):
    list_filter = (EmailMessageSentFilter, "service")
    search_fields = ("subject",)
    list_display = (
        "id",
        "subject",
        "service",
        "created",
        "ready_to_send",
        "sent",
        "last_attempt",
    )
