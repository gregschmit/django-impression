from django.contrib import admin
from django.db.models import TextField
from django.utils.translation import gettext_lazy as _

from . import models
from .widgets import TemplateEditorWidget


@admin.register(models.EmailAddress)
class EmailAddressAdmin(admin.ModelAdmin):
    list_filter = ("unsubscribed_from_all",)
    search_fields = ("email_address",)
    list_display = ("email_address", "unsubscribed_from_all")


@admin.register(models.Template)
class TemplateAdmin(admin.ModelAdmin):
    list_filter = ("extends",)
    search_fields = ("subject", "body", "extends")
    list_display = ("name", "subject", "extends")
    formfield_overrides = {TextField: {"widget": TemplateEditorWidget}}


@admin.register(models.Distribution)
class DistributionAdmin(admin.ModelAdmin):
    search_fields = list_display = ("name",)


@admin.register(models.RateLimit)
class RateLimitAdmin(admin.ModelAdmin):
    list_filter = ("name", "type")
    search_fields = ("name",)
    list_display = (
        "name",
        "rule",
    )


@admin.register(models.Service)
class ServiceAdmin(admin.ModelAdmin):
    list_filter = ("is_active", "allow_json_body", "template", "from_email_address")
    search_fields = ("name",)
    list_display = (
        "name",
        "is_active",
        "is_unsubscribable",
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
        "service",
        "subject",
        "created",
        "updated",
        "ready_to_send",
        "sent",
        "last_attempt",
    )
    fieldsets_without_readonly = (
        (None, {"fields": ("service",)}),
        (
            "Message Details",
            {
                "fields": (
                    "subject",
                    "body",
                    "override_from_email_address",
                    "extra_to_email_addresses",
                    "extra_cc_email_addresses",
                    "extra_bcc_email_addresses",
                )
            },
        ),
        ("Meta", {"fields": ("ready_to_send", "sent", "last_attempt")}),
    )
    fieldsets = (
        (None, {"fields": ("service", "_user_display")}),
        (
            "Message Details",
            {
                "fields": (
                    "subject",
                    "body",
                    "override_from_email_address",
                    "extra_to_email_addresses",
                    "extra_cc_email_addresses",
                    "extra_bcc_email_addresses",
                )
            },
        ),
        (
            "Meta",
            {
                "fields": (
                    "created",
                    "updated",
                    "ready_to_send",
                    "sent",
                    "last_attempt",
                ),
            },
        ),
        (
            "Final Properties",
            {
                "classes": ("collapse",),
                "fields": (
                    "final_subject",
                    "final_body",
                    "final_from_email_address",
                    "final_to_email_addresses",
                    "final_cc_email_addresses",
                    "final_bcc_email_addresses",
                ),
            },
        ),
    )
    readonly_fields = (
        "_user_display",
        "created",
        "updated",
        "final_subject",
        "final_body",
        "final_from_email_address",
        "final_to_email_addresses",
        "final_cc_email_addresses",
        "final_bcc_email_addresses",
    )

    def get_fieldsets(self, request, obj=None):
        """
        Hook for specifying fieldsets. Modified to use `fieldsets_without_readonly`.
        """
        if not obj:
            return self.fieldsets_without_readonly
        return super().get_fieldsets(request, obj=obj)

    def _user_display(self, obj):
        return obj.get_user_display()

    _user_display.short_description = "User"
