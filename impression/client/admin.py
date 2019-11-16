from django.contrib import admin

from . import models


@admin.register(models.RemoteImpressionServer)
class RemoteImpressionServerAdmin(admin.ModelAdmin):
    list_filter = []
    search_fields = ["name", "target", "authentication_token"]
    list_display = ["name", "is_active", "target", "authentication_token"]
