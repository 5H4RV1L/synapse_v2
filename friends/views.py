from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import FriendRequest
from django.views.decorators.http import require_POST
from notifications.utils import create_notification
from .models import Friend


@login_required
def send_friend_request(request, username):
    User = get_user_model()
    receiver = get_object_or_404(User, username=username)

    if receiver == request.user:
        return redirect('profile', username=username)

    # Already friends?
    if Friend.objects.filter(
        user1=request.user, user2=receiver
    ).exists() or Friend.objects.filter(
        user1=receiver, user2=request.user
    ).exists():
        return redirect('profile', username=username)

    # Check existing request in same direction
    existing_request = FriendRequest.objects.filter(
        sender=request.user,
        receiver=receiver
    ).first()

    if existing_request:
        if existing_request.status == 'rejected':
            existing_request.status = 'pending'
            existing_request.save()

            create_notification(
                user=receiver,
                sender=request.user,
                notification_type='friend_request'
            )

        return redirect('profile', username=username)

    # Check reverse direction request
    reverse_request = FriendRequest.objects.filter(
        sender=receiver,
        receiver=request.user
    ).first()

    if reverse_request:
        if reverse_request.status == 'rejected':
            # Flip the direction and reuse row
            reverse_request.sender = request.user
            reverse_request.receiver = receiver
            reverse_request.status = 'pending'
            reverse_request.save()

            create_notification(
                user=receiver,
                sender=request.user,
                notification_type='friend_request'
            )

        return redirect('profile', username=username)

    # No request exists in either direction → create new
    FriendRequest.objects.create(
        sender=request.user,
        receiver=receiver,
        status='pending'
    )

    create_notification(
        user=receiver,
        sender=request.user,
        notification_type='friend_request'
    )

    return redirect('profile', username=username)


@require_POST
@login_required
def accept_friend_request(request, request_id):
    friend_request = get_object_or_404(FriendRequest, id=request_id)

    if friend_request.receiver == request.user:
        friend_request.status = 'accepted'
        friend_request.save()

        Friend.objects.get_or_create(
            user1=friend_request.sender,
            user2=friend_request.receiver
        )

        create_notification(
            user=friend_request.sender,
            sender=request.user,
            notification_type='friend_accept'
        )

    return redirect('profile', username=friend_request.sender.username)


@require_POST
@login_required
def decline_friend_request(request, request_id):
    friend_request = get_object_or_404(FriendRequest, id=request_id)

    if friend_request.receiver == request.user:
        friend_request.status = 'rejected'
        friend_request.save()

    return redirect('profile', username=friend_request.sender.username)