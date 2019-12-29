from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class RateLimitQuerySet(models.QuerySet):
    def get_by_natural_key(self, name):
        return self.get(name=name)


class RateLimit(models.Model):
    """
    A definition for a rate limit on a service.
    """

    name = models.CharField(max_length=255, unique=True)
    TOTAL = 0
    PER_USER = 1
    PER_GROUP = 2
    GROUPING_CHOICES = (
        (TOTAL, _("total")),
        (PER_USER, _("per user")),
        (PER_GROUP, _("per group")),
    )
    grouping = models.IntegerField(
        choices=GROUPING_CHOICES,
        default=TOTAL,
        help_text=_(
            "Whether the rate limit should apply to all uses of the service (total), "
            "or on a per-group or per-user basis."
        ),
    )
    quantity = models.IntegerField(
        default=1,
        help_text=_(
            "The number of messages which can be sent to the service in the given time "
            "period (either block or rolling window)."
        ),
    )
    BLOCK_PERIOD = 0
    ROLLING_WINDOW = 1
    TYPE_CHOICES = (
        (BLOCK_PERIOD, _("Block Period")),
        (ROLLING_WINDOW, _("Rolling Window")),
    )
    type = models.IntegerField(choices=TYPE_CHOICES, default=BLOCK_PERIOD)
    HOUR = 0
    DAY = 1
    WEEK = 2
    MONTH = 3
    BLOCK_PERIOD_CHOICES = (
        (HOUR, _("per hour")),
        (DAY, _("per day")),
        (WEEK, _("per week")),
        (MONTH, _("per month")),
    )
    BLOCK_PERIOD_NAME = {id: name for id, name in BLOCK_PERIOD_CHOICES}
    block_period = models.IntegerField(choices=BLOCK_PERIOD_CHOICES, default=HOUR)
    rolling_window = models.DurationField(
        default=timezone.timedelta(hours=1), help_text=_("[DD] HH:MM:SS")
    )

    objects = RateLimitQuerySet.as_manager()

    def __str__(self):
        return self.name

    def get_timeframe(self, now=None):
        """
        Get a start and end datetime object (timezone aware) for the time frame we
        should be investigating for rate limit violations. If `now` is provided, use
        that, otherwise, use `timezone.now()``.

        This should return a tuple in the form (start_dt, end_dt).
        """
        if not now:
            now = timezone.now()
        if self.type == self.ROLLING_WINDOW:
            return (now - self.rolling_window, now)
        elif self.type == self.BLOCK_PERIOD:
            then = now.replace(microsecond=0, second=0, minute=0)
            if self.block_period == self.HOUR:
                return (then, now)
            else:
                then = then.replace(hour=0)
                if self.block_period == self.DAY:
                    return (then, now)
                else:
                    then = then.replace(hour=0, day=then.day - then.isoweekday())
                    if self.block_period == self.WEEK:
                        return (then, now)
                    else:
                        then = then.replace(day=1)
                        if self.block_period == self.MONTH:
                            return (then, now)
        raise Exception("RateLimit type or block period not known.")

    def humanized_rolling_window(self):
        """
        Human-readable summary of the rolling window.
        """
        minutes = self.rolling_window.seconds // 60
        remaining_seconds = self.rolling_window.seconds % 60
        hours = minutes // 60
        remaining_minutes = minutes % 60
        return "{} days, {} hours, {} minutes, {} seconds".format(
            self.rolling_window.days, hours, remaining_minutes, remaining_seconds
        )

    def rule(self):
        """
        Human-readable summary of this rate limit rule.
        """
        if self.type == self.BLOCK_PERIOD:
            return "{} messages {}".format(
                self.quantity, self.BLOCK_PERIOD_NAME[self.block_period]
            )
        if self.type == self.ROLLING_WINDOW:
            return "{} messages for a rolling window of: {}".format(
                self.quantity, self.humanized_rolling_window()
            )

    def check_service(self, service, user=None, groups=None):
        """
        Check the service to see if the rate limit has been reached, either in total,
        or per user or per group, depending on the configuration.

        Return True if the rate limit has not been reached and False if it has.
        """
        (then, now) = self.get_timeframe()
        base_query = service.messages.filter(created__gte=then, created__lte=now)
        if self.grouping == self.PER_USER and user:
            count = base_query.filter(
                user_type=ContentType.objects.get_for_model(user), user_id=user.pk
            ).count()
        elif self.grouping == self.PER_GROUP and groups:
            count = max([base_query.filter(user__groups=g).count() for g in groups])
        elif self.grouping == self.TOTAL:
            count = base_query.count()
        else:
            raise ValueError(
                "self.grouping is not a valid value (bad value {} for obj {})".format(
                    self.grouping, self.pk
                )
            )
        return count < self.quantity
