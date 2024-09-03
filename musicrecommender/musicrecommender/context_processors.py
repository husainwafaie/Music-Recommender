def spotify_user_context(request):
    if request.user.is_authenticated:
        spotify_logged_in = request.session.get('spotify_logged_in', False)
        user_profile = request.session.get('user_profile', None)
        return {
            'spotify_logged_in': spotify_logged_in,
            'user_profile': user_profile,
        }
    return {}
