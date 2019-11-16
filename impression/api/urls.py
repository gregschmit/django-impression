from django.urls import path

from .views import SendMessageAPIView


urlpatterns = [path("send_message/", SendMessageAPIView.as_view(), name="send_message")]
