from django.core.exceptions import PermissionDenied

from rest_framework import permissions, status
from rest_framework.exceptions import NotFound, Throttled
from rest_framework.response import Response
from rest_framework.views import APIView

from ..exceptions import RateLimitException
from ..models import EmailAddress, Message, Service


class SendMessageAPIView(APIView):
    """
    This API view is for external services that need to send email via this Impression
    server. This view enforces group permissions in accordance with the Service's
    allowed groups.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_view_name(self):
        return "Send Message API"

    def create_message(self, request, *args, **kwargs):
        """
        Create a message attached to a service. The service must either be identified in
        the URL pattern, or as a query parameter, or in the request data, all as the
        variable ``service_name``. The precedance is in that same order, so for example,
        if the service is defined in the URL parameter, then the service in the request
        data will be ignored.
        """

        # extract service name
        if "service_name" in self.kwargs:
            service_name = self.kwargs.get("service_name")
        elif "service_name" in request.query_params:
            service_name = request.query_params.get("service_name")
        elif "service_name" in request.data:
            service_name = request.data.get("service_name")
        else:
            raise NotFound("Target service name not provided.")

        # resolve to service, or raise error
        try:
            service = Service.objects.get(name=service_name)
        except (Service.DoesNotExist, ValueError, TypeError):
            raise NotFound("Target service not found.")

        # check for service-level permissions
        allowed_groups = service.allowed_groups.values_list("pk", flat=True)
        if not request.user.groups.filter(pk__in=allowed_groups):
            raise PermissionDenied()

        # build message
        message = Message(
            service=service,
            subject=request.data.get("subject", "") or "",
            body=request.data.get("body", "") or "",
        )
        from_email = request.data.get("from", None)
        if from_email:
            (
                message.override_from_email_address,
                created,
            ) = EmailAddress.objects.get_or_create(
                email_address=EmailAddress.extract_display_email(from_email)
            )
            if get_setting("IMPRESSION_DEFAULT_UNSUBSCRIBED") and created:
                message.override_from_email_address.update(unsubscribed_from_all=True)

        # try saving, handling RateLimitException
        try:
            message.save()
        except RateLimitException:
            raise Throttled(detail="Rate limit has been reached!")

        # convert email strings to email objects
        to_l = EmailAddress.filter_unsubscribed(
            EmailAddress.convert_emails(request.data.get("to", [])), service
        )
        cc_l = EmailAddress.filter_unsubscribed(
            EmailAddress.convert_emails(request.data.get("cc", [])), service
        )
        bcc_l = EmailAddress.filter_unsubscribed(
            EmailAddress.convert_emails(request.data.get("bcc", [])), service
        )

        # add emails to the message
        message.extra_to_email_addresses.add(*to_l)
        message.extra_cc_email_addresses.add(*cc_l)
        message.extra_bcc_email_addresses.add(*bcc_l)

        # signal message can be sent
        message.ready_to_send = True
        message.save()

        return Response({}, status=status.HTTP_201_CREATED)

    def get(self, request, *args, **kwargs):
        return self.options(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create_message(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.create_message(request, *args, **kwargs)
