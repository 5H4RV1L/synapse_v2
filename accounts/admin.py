from django.contrib import admin
from .models import User, InviteCode

admin.site.register(User)
admin.site.register(InviteCode)
