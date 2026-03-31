from django.contrib import admin
from .models import Post, Vote, Hashtag, PostHashtag

admin.site.register(Post)
admin.site.register(Vote)
admin.site.register(Hashtag)
admin.site.register(PostHashtag)
