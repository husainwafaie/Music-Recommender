from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm

# Create your views here.
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
                return redirect(mainpage)
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

@login_required
def mainpage(request):
    return render(request, "homepage.html")