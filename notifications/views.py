from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from .models import Notification
from django.http import JsonResponse


@login_required
def clear_notifications(request):
    if request.method == "POST":
        Notification.objects.filter(user=request.user).delete()
    return redirect('feed')


@login_required
def notifications_api(request):
    notifications = request.user.notifications.order_by('-created_at')[:20]

    data = []
    for n in notifications:
        data.append({
            "type": n.notification_type,
            "sender": n.sender.username if n.sender else "",
            "post_id": n.post.id if n.post else None,
            "chatroom_id": n.chatroom.id if n.chatroom else None,
            "chatroom_name": n.chatroom.name if n.chatroom else None,
        })

    return JsonResponse({
        "count": request.user.notifications.count(),
        "notifications": data
    })