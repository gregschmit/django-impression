from django.apps import AppConfig


class CustomAppConfig(AppConfig):
    name = "impression.client"
    label = "impression_client"
    verbose_name = "Impression Client"
