from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import RegistrationForm


class CineBookLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = AuthenticationForm
    redirect_authenticated_user = True

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['username'].widget.attrs.update(
            {'autocomplete': 'username', 'autofocus': True}
        )
        form.fields['password'].widget.attrs['autocomplete'] = 'current-password'
        return form

    def form_valid(self, form):
        messages.success(self.request, 'You are now signed in.')
        return super().form_valid(form)


def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Your CineBook account has been created.')
            return redirect('bookings:my_bookings')
    else:
        form = RegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been signed out.')
    return redirect('home')


@login_required
def profile(request):
    return render(
        request,
        'pages/placeholder.html',
        {
            'page_title': 'Your profile',
            'page_message': f'Signed in as {request.user.get_username()}. Profile settings are coming soon.',
        },
    )
