from django.db import models
from django.conf import settings
from PIL import Image

class Post(models.Model):
    
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )
    
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posts'
    )
    
    image = models.ImageField(
        upload_to='post_images/',
        null=True,
        blank=True
    )
    
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"Post by {self.author} at {self.created_at}"
    
    def score(self):
        return sum(v.vote_type for v in self.votes.all())
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
    
        if self.image:
            img = Image.open(self.image.path)
    
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
    
            img.thumbnail((800, 800))
            img.save(self.image.path, format='JPEG', quality=75)



class Vote(models.Model):
    VOTE_CHOICES = (
        (1, 'Upvote'),
        (-1, 'Downvote'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='votes'
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='votes'
    )
    vote_type = models.SmallIntegerField(choices=VOTE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')

    def __str__(self):
        return f"{self.user} voted {self.vote_type} on {self.post.id}"


class Hashtag(models.Model):
    tag = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"#{self.tag}"


class PostHashtag(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='post_hashtags'
    )
    hashtag = models.ForeignKey(
        Hashtag,
        on_delete=models.CASCADE,
        related_name='hashtag_posts'
    )

    class Meta:
        unique_together = ('post', 'hashtag')

    def __str__(self):
        return f"{self.post.id} → #{self.hashtag.tag}"
