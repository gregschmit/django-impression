from django.db import models
from django.db.utils import Error as DBError

from ..settings import get_setting


class RemoteImpressionServerQuerySet(models.QuerySet):
    def get_by_natural_key(self, name):
        return self.get(name=name)


class RemoteImpressionServer(models.Model):
    """
    Contains remote server definitions with authentication tokens. Impression will use
    the active server, or if none is active, then the ``IMPRESSION_DEFAULT_TARGET`` and
    ``IMPRESSION_DEFAULT_TOKEN`` Django settings values.
    """

    name = models.CharField(max_length=255, blank=False, unique=True)
    is_active = models.BooleanField(default=True)
    target = models.CharField(
        max_length=255, blank=False, default="http://127.0.0.1:8000/api/send_message/"
    )
    authentication_token = models.CharField(max_length=255, blank=False)

    objects = RemoteImpressionServerQuerySet.as_manager()

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)

    @classmethod
    def get_target_and_token(cls):
        """
        Return either the active model or settings-based target and token.
        """
        try:
            server = cls.objects.filter(is_active=True)
            if server:
                return (server[0].target, server[0].authentication_token)
        except DBError:  # database not being used; default to settings.py
            pass

        # return defaults
        return (
            get_setting("IMPRESSION_DEFAULT_TARGET"),
            get_setting("IMPRESSION_DEFAULT_TOKEN"),
        )

    def save(self, *args, **kwargs):
        """
        Add logic for maintaining at most 1 active instance.
        """
        actives = type(self).objects.filter(is_active=True).exclude(pk=self.pk)
        if self.is_active:
            actives.update(is_active=False)
        else:
            active = actives.first()
            actives.exclude(pk=active.pk).update(is_active=False)
        return super().save(*args, **kwargs)
