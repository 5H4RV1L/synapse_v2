from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from notifications.utils import create_notification
from .models import Post
from django.shortcuts import get_object_or_404
from .models import Vote
from friends.models import Friend
from django.db import models
from django.views.decorators.http import require_POST
from PIL import Image
from django.core.exceptions import ValidationError

def validate_image(file):
    if file.size > 2 * 1024 * 1024:
        raise ValidationError("Image too large")

    try:
        img = Image.open(file)
        img.verify()
    except:
        raise ValidationError("Invalid image")

@login_required
def feed(request):
    user = request.user

    friendships = Friend.objects.filter(
        models.Q(user1=user) | models.Q(user2=user)
    )

    friend_ids = []
    for f in friendships:
        if f.user1 == user:
            friend_ids.append(f.user2.id)
        else:
            friend_ids.append(f.user1.id)

    friend_ids.append(user.id)

    posts = Post.objects.filter(
        author__id__in=friend_ids,
        is_deleted=False
    ).order_by('-created_at')

    return render(request, 'posts/feed.html', {'posts': posts})

@login_required
def vote_post(request, post_id, vote_type):
    post = get_object_or_404(Post, id=post_id)

    vote_value = 1 if vote_type == 'up' else -1

    existing_vote = Vote.objects.filter(user=request.user, post=post).first()

    if existing_vote:
        if existing_vote.vote_type == vote_value:
            existing_vote.delete()
        else:
            existing_vote.vote_type = vote_value
            existing_vote.save()
    else:
        Vote.objects.create(user=request.user, post=post, vote_type=vote_value)
        
        if post.author != request.user:
            create_notification(
                user=post.author,
                sender=request.user,
                notification_type='upvote' if vote_value == 1 else 'downvote',
                post=post
            )

    return redirect('feed')

@login_required
def create_post_page(request):
    parent_id = request.GET.get('reply_to')

    parent_post = None
    if parent_id:
        parent_post = get_object_or_404(Post, id=parent_id)

    if request.method == 'POST':
        content = request.POST.get('content')
        image = request.FILES.get('image')
        
        if not content or len(content) > 1000:
            return redirect('feed')
        
        if image:
            try:
                validate_image(image)
            except ValidationError:
                return redirect('feed')

        new_post = Post.objects.create(
            author=request.user,
            content=content,
            image=image,
            parent=parent_post
        )

        friendships = Friend.objects.filter(
            models.Q(user1=request.user) | models.Q(user2=request.user)
        )

        for f in friendships:
            friend = f.user2 if f.user1 == request.user else f.user1

            create_notification(
                user=friend,
                sender=request.user,
                notification_type='new_post',
                post=new_post
            )

        if parent_post and parent_post.author != request.user:
            create_notification(
                user=parent_post.author,
                sender=request.user,
                notification_type='reply',
                post=new_post
            )

        return redirect('feed')

    return render(request, 'posts/create_post.html', {
        'parent_post': parent_post
    })

@require_POST
@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    # Only author can delete
    if post.author != request.user:
        return redirect('feed')

    post.is_deleted = True
    post.save()

    return redirect(request.META.get('HTTP_REFERER', 'feed'))
