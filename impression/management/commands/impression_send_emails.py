from django.core.management.base import BaseCommand
from django.db import Q, transaction

from ...models import Message


class Command(BaseCommand):
    help = "Send any unsent messages."

    def handle(self, *args, **kwargs):
        """
        This might seem weird, but we don't want to lock all messages and wrap them in a
        transaction, because then if only a few send but one fails, the database will
        reflect none being sent, and that could cause multiple send issues. We want to
        avoid that!

        So, we will get a "reference queryset" of messages that we think are unsent and
        ready to send, and we will iterate through those. With each one, we will start
        an atomic transaction, select_for_update the message, get it from the DB, and
        then send if it still meets the requirements.
        """
        q = Q(read_to_send=True, send__isnull=True)
        message_ids = Message.objects.filter(q).values_list("pk", flat=True)
        for message_id in message_ids:
            message_q = Message.objects.filter(pk=message_id)
            with transaction.atomic():
                try:
                    message = message_q.select_for_update().get(q)
                    message.send()
                except Message.DoesNotExist:
                    # state must have changed between our first query and this one
                    pass
