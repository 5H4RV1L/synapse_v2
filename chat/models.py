from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class ChatRoom(models.Model):
    name = models.CharField(max_length=50)
    password = models.CharField(max_length=4)  # 4-digit numeric password
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_chatrooms'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['expires_at']

    def save(self, *args, **kwargs):
        if not self.pk:
            self.expires_at = timezone.now() + timedelta(hours=1)
        super().save(*args, **kwargs)

    def time_remaining_seconds(self):
        delta = self.expires_at - timezone.now()
        return max(int(delta.total_seconds()), 0)

    def __str__(self):
        return self.name


class ChatRoomMember(models.Model):
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='members'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chatroom_memberships'
    )
    joined_via_invite = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('room', 'user')

    def __str__(self):
        return f"{self.user.username} in {self.room.name}"


class ChatRoomMessage(models.Model):
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username} in {self.room.name}: {self.content[:30]}"