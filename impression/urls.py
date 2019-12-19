from django.urls import include, path

from impression.admin_ui.sites import custom_admin_site

urlpatterns = [
    path("admin/", custom_admin_site.urls),
    path("api/", include("impression.api.urls")),
]
