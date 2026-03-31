from .models import Notification


def create_notification(user, sender, notification_type, post=None, chatroom=None):
    Notification.objects.create(
        user=user,
        sender=sender,
        notification_type=notification_type,
        post=post,
        chatroom=chatroom,
    )