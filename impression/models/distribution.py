from django.db import models


class DistributionQuerySet(models.QuerySet):
    def get_by_natural_key(self, name):
        return self.get(name=name)


class Distribution(models.Model):
    """
    A collection of email addresses (and/or other distributions).
    """

    name = models.CharField(max_length=255, unique=True)
    email_addresses = models.ManyToManyField("impression.EmailAddress", blank=True)
    distributions = models.ManyToManyField("self", symmetrical=False, blank=True)

    objects = DistributionQuerySet.as_manager()

    def natural_key(self):
        return (self.name,)

    def collect_email_addresses(self, already_collected=None):
        """
        Collect emails and distributions, recursively. Return a set of EmailAddress
        objects.
        """
        if not already_collected:
            already_collected = set([self])
        else:
            already_collected.add(self)
        r = set(self.email_addresses.all())
        for d in self.distributions.all():
            if not d in already_collected:
                r |= d.collect_email_addresses(already_collected)
        return r

    def __str__(self):
        return self.name
