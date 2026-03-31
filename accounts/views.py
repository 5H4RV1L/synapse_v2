from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from friends.models import FriendRequest, Friend
from posts.models import Post
from django.contrib.auth import get_user_model, login
from django.contrib import messages
from django.core.mail import send_mail
from .models import EmailOTP
from django.utils import timezone
from datetime import timedelta
from PIL import Image
from django.core.exceptions import ValidationError
import time

def validate_image(file):
    if file.size > 2 * 1024 * 1024:
        raise ValidationError("Image too large")

    try:
        img = Image.open(file)
        img.verify()
    except:
        raise ValidationError("Invalid image")

def send_otp_email(email, purpose):
    # Rate-limit: don't send if a code was created in the last 60 seconds
    recent = EmailOTP.objects.filter(
        email=email,
        purpose=purpose,
        is_used=False,
        created_at__gte=timezone.now() - timedelta(seconds=60)
    )
    if recent.exists():
        return None

    # Invalidate any older unused codes
    EmailOTP.objects.filter(
        email=email,
        purpose=purpose,
        is_used=False
    ).delete()

    code = EmailOTP.generate_code()
    otp = EmailOTP.objects.create(
        email=email,
        code=code,
        purpose=purpose
    )

    send_mail(
        "Your OTP Code",
        f"Your verification code is: {code}\n\nValid for 5 minutes.",
        None,
        [email],
    )

    return otp

@login_required
def profile(request, username):
    User = get_user_model()
    profile_user = get_object_or_404(User, username=username)

    is_friend = Friend.objects.filter(
        Q(user1=request.user, user2=profile_user) |
        Q(user1=profile_user, user2=request.user)
    ).exists()
    
    if request.user == profile_user or is_friend:
        posts = Post.objects.filter(
            author=profile_user,
            is_deleted=False
        ).order_by('-created_at')
    else:
        posts = Post.objects.none()

    is_friend = Friend.objects.filter(
        Q(user1=request.user, user2=profile_user) |
        Q(user1=profile_user, user2=request.user)
    ).exists()

    sent_request = FriendRequest.objects.filter(
        sender=request.user,
        receiver=profile_user,
        status='pending'
    ).first()

    received_request = FriendRequest.objects.filter(
        sender=profile_user,
        receiver=request.user,
        status='pending'
    ).first()
    
    friends = []

    if request.user == profile_user:
        friendships = Friend.objects.filter(
            Q(user1=profile_user) | Q(user2=profile_user)
        )
    
        for f in friendships:
            friends.append(
                f.user2 if f.user1 == profile_user else f.user1
            )

    context = {
        'profile_user': profile_user,
        'posts': posts,
        'is_friend': is_friend,
        'sent_request': sent_request,
        'received_request': received_request,
        'friends': friends,
    }

    return render(request, 'accounts/profile.html', context)

@login_required
def search_profile(request):
    username = request.GET.get('username')
    if username:
        return redirect('profile', username=username)
    return redirect('feed')

@login_required
def search_page(request):
    query = request.GET.get('q')
    results = None
    friends = None

    if query:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        results = User.objects.filter(username__icontains=query)
    else:
        from friends.models import Friend
        friendships = Friend.objects.filter(
            Q(user1=request.user) | Q(user2=request.user)
        )
        friends = []
        for f in friendships:
            friends.append(f.user1 if f.user2 == request.user else f.user2)

    return render(request, 'accounts/search.html', {
        'results': results,
        'friends': friends
    })

@login_required
def settings_page(request):
    return render(request, 'accounts/settings.html')


@login_required
def change_theme(request):
    if request.method == 'POST':
        theme = request.POST.get('theme', 'dark')
        valid_themes = ['dark', 'neo-brutalism', 'joyce']
        if theme in valid_themes:
            request.user.theme_preference = theme
            request.user.save()
    return redirect('profile', username=request.user.username)


@login_required
def toggle_theme(request):
    user = request.user
    if user.theme_preference == 'light':
        user.theme_preference = 'dark'
    else:
        user.theme_preference = 'light'
    user.save()

    return redirect('settings_page')


@login_required
def set_theme(request):
    if request.method == 'POST':
        theme = request.POST.get('theme', 'scifi')
        user = request.user
        user.theme_preference = theme
        user.save()
    
    return redirect('settings_page')


def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        User = get_user_model()

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect('signup')
        
        if len(username) > 12:
            messages.error(request, "Username must be 1-12 characters.")
            return redirect('signup')

        if not (8 <= len(password) <= 16):
            messages.error(request, "Password must be between 8 and 16 characters.")
            return redirect('signup')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('signup')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=False
        )

        send_otp_email(email, 'signup')

        request.session['verify_email'] = email

        return redirect('verify_otp')

    return render(request, 'accounts/signup.html')

@login_required
def change_profile_photo(request):
    if request.method == 'POST':
        image = request.FILES.get('profile_photo')

        if image:
            try:
                validate_image(image)
            except ValidationError:
                return redirect('profile', username=request.user.username)

            request.user.profile_photo = image
            request.user.save()

    return redirect('profile', username=request.user.username)

def verify_otp(request):
    email = request.session.get('verify_email')

    if not email:
        return redirect('signup')

    if request.method == 'POST':
        
        last_attempt = request.session.get('otp_last_attempt')
        now = time.time()

        if last_attempt and now - last_attempt < 2:
            messages.error(request, "Too fast. Wait 2 seconds.")
            return redirect('verify_otp')

        request.session['otp_last_attempt'] = now
        
        code = request.POST.get('otp')

        otp = EmailOTP.objects.filter(
            email=email,
            purpose='signup',
            is_used=False
        ).first()

        if not otp:
            messages.error(request, "Invalid or expired OTP.")
            return redirect('verify_otp')

        # Check if too many attempts
        if otp.attempts >= 5:
            messages.error(request, "Too many incorrect attempts. Request a new OTP.")
            return redirect('signup')

        # If code doesn't match
        if otp.code != code:
            otp.attempts += 1
            otp.save()
            messages.error(request, "Invalid OTP.")
            return redirect('verify_otp')

        # Check expiry
        if otp.is_expired():
            messages.error(request, "OTP expired.")
            return redirect('signup')

        User = get_user_model()
        user = User.objects.get(email=email)
        user.is_active = True
        user.save()

        otp.is_used = True
        otp.save()

        login(request, user)

        del request.session['verify_email']

        return redirect('feed')

    return render(request, 'accounts/verify_otp.html')

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')

        User = get_user_model()

        if User.objects.filter(email=email).exists():
            send_otp_email(email, 'reset')
            request.session['reset_email'] = email

        return redirect('verify_reset_otp')

    return render(request, 'accounts/forgot_password.html')

def verify_reset_otp(request):
    email = request.session.get('reset_email')

    if not email:
        return redirect('forgot_password')

    if request.method == 'POST':
        code = request.POST.get('otp')

        otp = EmailOTP.objects.filter(
            email=email,
            purpose='reset',
            is_used=False
        ).first()
    
        if not otp:
            messages.error(request, "Invalid or expired OTP.")
            return redirect('verify_reset_otp')
    
        if otp.attempts >= 5:
            messages.error(request, "Too many incorrect attempts. Request a new OTP.")
            return redirect('forgot_password')
    
        if otp.code != code:
            otp.attempts += 1
            otp.save()
            messages.error(request, "Invalid OTP.")
            return redirect('verify_reset_otp')
    
        if otp.is_expired():
            messages.error(request, "OTP expired.")
            return redirect('forgot_password')
    
        otp.is_used = True
        otp.save()

        request.session['allow_password_reset'] = True

        return redirect('reset_password')

    return render(request, 'accounts/verify_reset_otp.html')

def reset_password(request):
    if not request.session.get('allow_password_reset'):
        return redirect('forgot_password')

    if request.method == 'POST':
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('reset_password')

        if not (4 <= len(password) <= 16):
            messages.error(request, "Password must be 4-16 characters.")
            return redirect('reset_password')

        email = request.session.get('reset_email')
        User = get_user_model()
        user = User.objects.get(email=email)

        user.set_password(password)
        user.save()

        del request.session['reset_email']
        del request.session['allow_password_reset']

        return redirect('login')

    return render(request, 'accounts/reset_password.html')