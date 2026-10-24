from django.shortcuts import render


def my_bookings(request):
    return render(
        request,
        'pages/placeholder.html',
        {
            'page_title': 'My bookings',
            'page_message': 'Your bookings will appear here once booking flows are available.',
        },
    )
