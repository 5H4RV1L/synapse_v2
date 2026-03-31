from django.db import models
from django.conf import settings


class Notification(models.Model):

    NOTIFICATION_TYPES = (
        ('friend_request', 'Friend Request'),
        ('friend_accept', 'Friend Accept'),
        ('upvote', 'Upvote'),
        ('downvote', 'Downvote'),
        ('new_post', 'New Post'),
        ('reply', 'Reply'),
        ('chatroom_invite', 'Chatroom Invite'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_notifications',
        null=True,
        blank=True
    )

    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES
    )

    post = models.ForeignKey(
        'posts.Post',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    chatroom = models.ForeignKey(
        'chat.ChatRoom',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender} → {self.user} ({self.notification_type})"