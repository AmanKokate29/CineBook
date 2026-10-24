from django.shortcuts import render


def home(request):
    return render(request, 'pages/home.html')


def movie_list(request):
    return render(
        request,
        'pages/placeholder.html',
        {
            'page_title': 'Explore movies',
            'page_message': 'Movie listings will appear here once the catalogue is ready.',
        },
    )
