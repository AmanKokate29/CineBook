from django.shortcuts import render


def login(request):
    return render(
        request,
        'pages/placeholder.html',
        {
            'page_title': 'Sign in',
            'page_message': 'Sign-in is not available yet. Account features are coming soon.',
        },
    )


def profile(request):
    return render(
        request,
        'pages/placeholder.html',
        {
            'page_title': 'Your profile',
            'page_message': 'Profile features are coming soon.',
        },
    )
