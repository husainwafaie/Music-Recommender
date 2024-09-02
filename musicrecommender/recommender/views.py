import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm

def index(request):
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
        
        # Refresh token if necessary
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
    
    return redirect(mainpage)

@login_required
def top_songs(request):
    token_info = request.session.get('token_info', None)
    sp = spotipy.Spotify(auth=token_info['access_token'])

    results = sp.current_user_top_tracks(limit=20, time_range='medium_term')
    top_tracks = results['items']

    for track in top_tracks:
        duration_ms = track['duration_ms']
        minutes = duration_ms // 60000
        seconds = (duration_ms // 1000) % 60
        track['duration'] = f"{minutes}:{seconds:02d}"  # Format as "minutes:seconds"

    return render(request, 'top_songs.html', {'top_tracks': top_tracks})

@login_required
def top_artists(request):
    token_info = request.session.get('token_info', None)
    sp = spotipy.Spotify(auth=token_info['access_token'])

    results = sp.current_user_top_artists(limit=10, time_range='medium_term')
    top_artists = results['items']

    return render(request, 'top_artists.html', {'top_artists': top_artists})
