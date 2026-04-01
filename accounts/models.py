from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from cloudinary.models import CloudinaryField

class User(AbstractUser):
    
    username = models.CharField(
        max_length=12,
        unique=True
    )
    

    profile_photo = CloudinaryField('image', null=True, blank=True)
    
    THEME_CHOICES = (
        ('dark', 'Cyberpunk Dark'),
        ('neo-brutalism', 'Neo Brutalism'),
        ('joyce', 'Joyce'),
    )

    theme_preference = models.CharField(
        max_length=20,
        choices=THEME_CHOICES,
        default='dark'
    )

    def __str__(self):
        return self.username
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

class InviteCode(models.Model):
    code = models.CharField(max_length=50, unique=True, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_invites'
    )
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='used_invite'
    )
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = uuid.uuid4().hex[:12]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code
    
import random
from django.utils import timezone
from datetime import timedelta

class EmailOTP(models.Model):
    PURPOSE_CHOICES = (
        ('signup', 'Signup'),
        ('reset', 'Password Reset'),
    )

    email = models.EmailField()
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=5)

    @staticmethod
    def generate_code():
        return str(random.randint(100000, 999999))
