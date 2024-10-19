import os
import spotipy
import json
from spotipy.oauth2 import SpotifyOAuth
from django.contrib.auth.models import User
from django.core.mail import send_mail, EmailMessage
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.utils.crypto import get_random_string
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from functools import wraps
import re
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


# decorator to check if the user is authenticated with spotify
def spotify_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        token_info = request.session.get('token_info')
        if not token_info:
            return redirect('home')  # redirect to home page if not logged in to Spotify
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password1']
        confirm_password = request.POST['password2']

        if password == confirm_password:
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already taken')
            elif User.objects.filter(email=email).exists():
                messages.error(request, 'Email already registered')
            else:

                otp = get_random_string(length=6, allowed_chars='0123456789')
                request.session['otp'] = otp
                request.session['username'] = username
                request.session['user_data'] = {'username' : username, 
                                                'password' : password, 
                                                'email' : email}
                send_mail(
                    'SpotAI Account Verification',
                    f'Your one-time passcode (OTP) is: {otp}',
                    'noreply@spotai.com',
                    [email],
                    fail_silently=False,
                )

                return redirect('verify_otp')
        else:
            messages.error(request, 'Passwords do not match')

    return render(request, 'register.html')



def verify_otp_view(request):
    if request.method == 'POST':
        otp = request.POST['otp']
        if otp == request.session.get('otp'):
            user_data = request.session.get('user_data')
            if user_data:
                user = User.objects.create_user(
                    username=user_data['username'],
                    email=user_data['email'],
                    password=user_data['password']
                )
                user.is_active = True 
                user.save()

                login(request, user)
                messages.success(request, 'Account verified successfully!')

                request.session.pop('otp', None)
                request.session.pop('user_data', None)

                return redirect('home')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')

    return render(request, 'verify_otp.html')



def get_spotify_client(token_info):
    sp_oauth = SpotifyOAuth(
        client_id=os.getenv('SPOTIPY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIPY_CLIENT_SECRET'),
        redirect_uri=os.getenv('SPOTIPY_REDIRECT_URI')
    )
    
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    user_profile = sp.current_user()
    
    return sp, user_profile, token_info

def index(request):
    list(messages.get_messages(request)) # to reset my messages
    if request.user.is_authenticated:
        return redirect('home')
    return redirect(login_view)

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

@login_required
def mainpage(request):
    token_info = request.session.get('token_info', None)

    if token_info:
        sp_oauth = SpotifyOAuth(
            client_id=os.getenv('SPOTIPY_CLIENT_ID'),
            client_secret=os.getenv('SPOTIPY_CLIENT_SECRET'),
            redirect_uri=os.getenv('SPOTIPY_REDIRECT_URI')
        )
        
        if sp_oauth.is_token_expired(token_info):
            token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
            request.session['token_info'] = token_info
        
        sp = spotipy.Spotify(auth=token_info['access_token'])
        user_profile = sp.current_user()
        
        return render(request, "homepage.html", {
            'spotify_logged_in': True,
            'user_profile': user_profile
        })
    else:
        return render(request, "homepage.html", {'spotify_logged_in': False})

@login_required
def spotify_login(request):
    sp_oauth = SpotifyOAuth(
        client_id=os.getenv('SPOTIPY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIPY_CLIENT_SECRET'),
        redirect_uri=os.getenv('SPOTIPY_REDIRECT_URI'),
        scope='user-library-read user-top-read'
    )
    
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

def spotify_callback(request):
    sp_oauth = SpotifyOAuth(
        client_id=os.getenv('SPOTIPY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIPY_CLIENT_SECRET'),
        redirect_uri=os.getenv('SPOTIPY_REDIRECT_URI')
    )
    
    code = request.GET.get('code')
    token_info = sp_oauth.get_access_token(code)
    request.session['token_info'] = token_info
    
    return redirect('home')

@login_required
@spotify_login_required
def top_songs(request):
    token_info = request.session.get('token_info', None)
    theme = request.session.get('theme', 'dark')
    sp, user_profile, token_info = get_spotify_client(token_info)

    results = sp.current_user_top_tracks(limit=20, time_range='medium_term')
    top_tracks = results['items']

    for track in top_tracks:
        duration_ms = track['duration_ms']
        minutes = duration_ms // 60000
        seconds = (duration_ms // 1000) % 60
        track['duration'] = f"{minutes}:{seconds:02d}"

    return render(request, 'top_songs.html', {
        'top_tracks': top_tracks,
        'spotify_logged_in': True,
        'user_profile': user_profile,
        'theme': theme
    })

@login_required
@spotify_login_required
def top_artists(request):
    token_info = request.session.get('token_info', None)
    theme = request.session.get('theme', 'dark')
    sp, user_profile, token_info = get_spotify_client(token_info)

    results = sp.current_user_top_artists(limit=10, time_range='medium_term')
    top_artists = results['items']

    return render(request, 'top_artists.html', {
        'top_artists': top_artists,
        'spotify_logged_in': True,
        'user_profile': user_profile,
        'theme': theme
    })


def light_dark_mode(request):
    return render(request, 'light_dark_mode.html')

@login_required
@spotify_login_required
def top_albums(request):
    token_info = request.session.get('token_info', None)
    sp = spotipy.Spotify(auth=token_info['access_token'])
    sp, user_profile, token_info = get_spotify_client(token_info)
    results = sp.current_user_saved_albums(limit=10)
    top_albums = [album['album'] for album in results['items']]

    return render(request, 'top_albums.html', {
        'top_albums': top_albums,
        'spotify_logged_in': True,
        'user_profile': user_profile
    })

@login_required
@spotify_login_required
def my_taste(request):
    token_info = request.session.get('token_info', None)
    sp, user_profile, token_info = get_spotify_client(token_info)
    
    top_artists = sp.current_user_top_artists(limit=50, time_range='long_term')
    genre_data = {}
    for artist in top_artists['items']:
        for genre in artist['genres']:
            genre_data[genre] = genre_data.get(genre, 0) + 1

    top_tracks = sp.current_user_top_tracks(limit=50, time_range='long_term')
    decade_data = {}
    for track in top_tracks['items']:
        release_year = int(track['album']['release_date'][:4])
        decade = (release_year // 10) * 10
        decade_data[decade] = decade_data.get(decade, 0) + 1

    track_ids = [track['id'] for track in top_tracks['items']]
    features = sp.audio_features(track_ids)
    avg_danceability = sum([f['danceability'] for f in features]) / len(features)
    avg_energy = sum([f['energy'] for f in features]) / len(features)
    avg_valence = sum([f['valence'] for f in features]) / len(features)

    genre_data_filtered = dict(sorted(genre_data.items(), key=lambda item: item[1], reverse=True)[:10])
    return render(request, 'my_taste.html', {
        'spotify_logged_in': True,
        'user_profile': user_profile,
        'genre_data': json.dumps(genre_data_filtered),
        'decade_data': json.dumps(decade_data),
        'avg_danceability': avg_danceability,
        'avg_energy': avg_energy,
        'avg_valence': avg_valence,
    })

def my_info(request):
    context = {
        'name': 'Husain Wafaie',
        'image_url': '/static/assets/Husain-pic.jpg',
        'bio': """
        I am a software developer with a passion for AI, 
        full-stack development, and solving complex problems 
        through technology. 
        I graduated from UC Irvine with a CS major, and I love 
        to explore 
        new technologies and build projects that make an impact.
        """
    }
    return render(request, "my_info.html", context)

@login_required
@spotify_login_required
def coming_soon_view(request):
    return render(request, 'coming_soon.html')

@login_required
def faq_page(request):
    return render(request, 'faq.html')

@login_required
def logout_view(request):
    request.session.flush() 
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('index')

def guide_view(request):
    return render(request, 'guide.html')

def contact_us_view(request):
    if request.method == 'POST':
        name = request.POST['name']
        email = request.POST['email']
        subject = request.POST['subject']
        message = request.POST['message']

        try:
            send_mail(
                subject=f"{subject} (From: {name}, {email})",
                message=message,
                from_email=email,
                recipient_list=['husainwafaie@gmail.com'],
                fail_silently=False,
            )
            messages.success(request, 'Your message has been sent successfully!')
        except Exception as e:
            messages.error(request, f'There was an error sending your message: {str(e)}')
        
        return redirect('contact_us')

    return render(request, 'contact_us.html')

@csrf_exempt
def send_reset_otp(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        email = data.get('email')
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'No account found with this email.'})
        
        otp = get_random_string(length=6, allowed_chars='0123456789')
        request.session['reset_otp'] = otp
        request.session['reset_email'] = email
        
        send_mail(
            'Password Reset OTP',
            f'Your OTP for password reset is: {otp}',
            'noreply@spotai.com',
            [email],
            fail_silently=False,
        )
        
        return JsonResponse({'success': True, 'message': 'OTP sent successfully.'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

@csrf_exempt
def verify_reset_otp(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        otp = data.get('otp')
        
        if otp == request.session.get('reset_otp'):
            return JsonResponse({'success': True, 'message': 'OTP verified successfully.'})
        else:
            return JsonResponse({'success': False, 'message': 'Invalid OTP.'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

def is_password_valid(password):
    min_length = 8
    has_uppercase = any(char.isupper() for char in password)
    has_lowercase = any(char.islower() for char in password)
    has_number = any(char.isdigit() for char in password)
    has_special_char = any(char in "@$!%*?&#" for char in password)

    if len(password) < min_length:
        return False, "Password must be at least 8 characters long"
    if not has_uppercase:
        return False, "Password must contain at least one uppercase letter"
    if not has_lowercase:
        return False, "Password must contain at least one lowercase letter"
    if not has_number:
        return False, "Password must contain at least one number"
    if not has_special_char:
        return False, "Password must contain at least one special character (@$!%*?&)"

    return True, ""

@csrf_exempt
def reset_password(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        
        if new_password != confirm_password:
            return JsonResponse({'success': False, 'message': 'Passwords do not match.'})
        
        is_valid, error_message = is_password_valid(new_password)
        if not is_valid:
            return JsonResponse({'success': False, 'message': error_message})
        
        email = request.session.get('reset_email')
        if not email:
            return JsonResponse({'success': False, 'message': 'Session expired. Please start over or refresh the page.'})
        
        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()
            
            del request.session['reset_otp']
            del request.session['reset_email']
            
            return JsonResponse({'success': True, 'message': 'Password reset successfully.'})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'User not found.'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})
