from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Q

from .models import ChatRoom, ChatRoomMember, ChatRoomMessage
from notifications.utils import create_notification
from friends.models import Friend

MAX_CREATED = 2
MAX_JOINED = 5


def expire_old_chatrooms():
    """Hard-delete expired chatrooms (called lazily on every chatroom view)."""
    ChatRoom.objects.filter(expires_at__lte=timezone.now(), is_active=True).update(is_active=False)
    # Hard delete inactive rooms + cascade deletes members & messages
    ChatRoom.objects.filter(is_active=False).delete()


def get_active_rooms_for_user(user):
    """Return active chatrooms the user is a member of."""
    return ChatRoom.objects.filter(
        members__user=user,
        is_active=True
    ).distinct()


@login_required
def chatrooms_page(request):
    expire_old_chatrooms()
    user = request.user

    my_rooms = get_active_rooms_for_user(user)

    # Annotate time remaining for template
    rooms_data = []
    for room in my_rooms:
        rooms_data.append({
            'room': room,
            'seconds_remaining': room.time_remaining_seconds(),
            'is_creator': room.creator == user,
        })

    context = {
        'rooms_data': rooms_data,
        'created_count': ChatRoom.objects.filter(creator=user, is_active=True).count(),
        'joined_count': my_rooms.count(),
        'max_created': MAX_CREATED,
        'max_joined': MAX_JOINED,
    }
    return render(request, 'chat/chat.html', context)


@login_required
@require_POST
def create_chatroom(request):
    expire_old_chatrooms()
    user = request.user

    created_count = ChatRoom.objects.filter(creator=user, is_active=True).count()
    if created_count >= MAX_CREATED:
        return JsonResponse({'error': f'You can only create {MAX_CREATED} active chatrooms.'}, status=400)

    name = request.POST.get('name', '').strip()
    password = request.POST.get('password', '').strip()

    if not name or len(name) > 50:
        return JsonResponse({'error': 'Name must be 1–50 characters.'}, status=400)

    if not password.isdigit() or len(password) != 4:
        return JsonResponse({'error': 'Password must be exactly 4 digits.'}, status=400)

    # Unique active name check
    if ChatRoom.objects.filter(name__iexact=name, is_active=True).exists():
        return JsonResponse({'error': 'A chatroom with that name already exists.'}, status=400)

    joined_count = ChatRoomMember.objects.filter(user=user).count()
    if joined_count >= MAX_JOINED:
        return JsonResponse({'error': f'You can only be in {MAX_JOINED} chatrooms at once.'}, status=400)

    room = ChatRoom.objects.create(name=name, password=password, creator=user)
    ChatRoomMember.objects.create(room=room, user=user, joined_via_invite=True)

    return JsonResponse({
        'success': True,
        'room_id': room.id,
        'room_name': room.name,
        'seconds_remaining': room.time_remaining_seconds(),
    })


@login_required
def chatroom_detail(request, room_id):
    expire_old_chatrooms()
    room = get_object_or_404(ChatRoom, id=room_id, is_active=True)

    if not ChatRoomMember.objects.filter(room=room, user=request.user).exists():
        return redirect('chatrooms')

    User = get_user_model()
    # Friends of the user who are NOT yet members
    friendships = Friend.objects.filter(
        Q(user1=request.user) | Q(user2=request.user)
    )
    friend_users = []
    for f in friendships:
        friend = f.user1 if f.user2 == request.user else f.user2
        if not ChatRoomMember.objects.filter(room=room, user=friend).exists():
            friend_users.append(friend)

    members = ChatRoomMember.objects.filter(room=room).select_related('user')

    context = {
        'room': room,
        'seconds_remaining': room.time_remaining_seconds(),
        'members': members,
        'friends_to_invite': friend_users,
        'is_creator': room.creator == request.user,
    }
    return render(request, 'chat/room.html', context)


@login_required
@require_POST
def join_chatroom(request, room_id):
    expire_old_chatrooms()
    room = get_object_or_404(ChatRoom, id=room_id, is_active=True)

    if ChatRoomMember.objects.filter(room=room, user=request.user).exists():
        return JsonResponse({'error': 'Already a member.'}, status=400)

    joined_count = ChatRoomMember.objects.filter(user=request.user).count()
    if joined_count >= MAX_JOINED:
        return JsonResponse({'error': f'You can only join {MAX_JOINED} chatrooms at once.'}, status=400)

    password = request.POST.get('password', '').strip()
    if password != room.password:
        return JsonResponse({'error': 'Incorrect password.'}, status=403)

    ChatRoomMember.objects.create(room=room, user=request.user)
    return JsonResponse({'success': True, 'room_id': room.id})


@login_required
def join_via_invite(request, room_id):
    """Join without password (invited users)."""
    expire_old_chatrooms()
    room = get_object_or_404(ChatRoom, id=room_id, is_active=True)

    if ChatRoomMember.objects.filter(room=room, user=request.user).exists():
        return redirect('chatroom_detail', room_id=room_id)

    joined_count = ChatRoomMember.objects.filter(user=request.user).count()
    if joined_count >= MAX_JOINED:
        return redirect('chatrooms')

    ChatRoomMember.objects.create(room=room, user=request.user, joined_via_invite=True)
    return redirect('chatroom_detail', room_id=room_id)


@login_required
@require_POST
def leave_chatroom(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id, is_active=True)
    ChatRoomMember.objects.filter(room=room, user=request.user).delete()

    # If creator leaves, delete the room entirely
    if room.creator == request.user:
        room.delete()

    return JsonResponse({'success': True})


@login_required
@require_POST
def invite_to_chatroom(request, room_id):
    expire_old_chatrooms()
    room = get_object_or_404(ChatRoom, id=room_id, is_active=True)

    if not ChatRoomMember.objects.filter(room=room, user=request.user).exists():
        return JsonResponse({'error': 'You are not in this room.'}, status=403)

    User = get_user_model()
    invitee_username = request.POST.get('username', '').strip()
    invitee = get_object_or_404(User, username=invitee_username)

    if invitee == request.user:
        return JsonResponse({'error': 'Cannot invite yourself.'}, status=400)

    if ChatRoomMember.objects.filter(room=room, user=invitee).exists():
        return JsonResponse({'error': 'User is already in the room.'}, status=400)

    # Only friends can be invited
    is_friend = Friend.objects.filter(
        Q(user1=request.user, user2=invitee) | Q(user1=invitee, user2=request.user)
    ).exists()
    if not is_friend:
        return JsonResponse({'error': 'You can only invite friends.'}, status=403)

    create_notification(
        user=invitee,
        sender=request.user,
        notification_type='chatroom_invite',
        chatroom=room,
    )

    return JsonResponse({'success': True})


@login_required
def get_room_messages(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id, is_active=True)
    if not ChatRoomMember.objects.filter(room=room, user=request.user).exists():
        return JsonResponse({'error': 'Forbidden'}, status=403)

    msgs = ChatRoomMessage.objects.filter(room=room).order_by('-created_at')[:50]
    data = [
        {
            'user': m.user.username,
            'content': m.content,
            'time': timezone.localtime(m.created_at).strftime('%H:%M'),
        }
        for m in reversed(list(msgs))
    ]
    return JsonResponse({
        'messages': data,
        'seconds_remaining': room.time_remaining_seconds(),
    })


@login_required
@require_POST
def send_room_message(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id, is_active=True)
    if not ChatRoomMember.objects.filter(room=room, user=request.user).exists():
        return JsonResponse({'error': 'Forbidden'}, status=403)

    content = request.POST.get('content', '').strip()
    if content:
        ChatRoomMessage.objects.create(room=room, user=request.user, content=content)

    return JsonResponse({'status': 'ok'})


@login_required
def search_chatrooms(request):
    expire_old_chatrooms()
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'rooms': []})

    rooms = ChatRoom.objects.filter(name__icontains=query, is_active=True)
    user_member_ids = set(
        ChatRoomMember.objects.filter(user=request.user).values_list('room_id', flat=True)
    )

    data = [
        {
            'id': r.id,
            'name': r.name,
            'members': r.members.count(),
            'seconds_remaining': r.time_remaining_seconds(),
            'is_member': r.id in user_member_ids,
        }
        for r in rooms
    ]
    return JsonResponse({'rooms': data})