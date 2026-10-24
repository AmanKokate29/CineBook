from django.db import models
from django.db.models import Q

from movies.models import Movie


class Theatre(models.Model):
    name = models.CharField(max_length=150)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)

    class Meta:
        ordering = ['city', 'name']
        indexes = [
            models.Index(fields=['city', 'name'], name='theatre_city_name_idx'),
        ]

    def __str__(self):
        return f'{self.name} ({self.city})'


class Screen(models.Model):
    theatre = models.ForeignKey(
        Theatre,
        on_delete=models.PROTECT,
        related_name='screens',
    )
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ['theatre', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['theatre', 'name'],
                name='unique_screen_name_per_theatre',
            ),
        ]

    def __str__(self):
        return f'{self.theatre.name} - {self.name}'


class Seat(models.Model):
    class SeatType(models.TextChoices):
        STANDARD = 'standard', 'Standard'
        PREMIUM = 'premium', 'Premium'
        ACCESSIBLE = 'accessible', 'Accessible'

    screen = models.ForeignKey(
        Screen,
        on_delete=models.PROTECT,
        related_name='seats',
    )
    row_identifier = models.CharField(max_length=10)
    seat_number = models.PositiveSmallIntegerField()
    seat_type = models.CharField(
        max_length=20,
        choices=SeatType.choices,
        default=SeatType.STANDARD,
    )

    class Meta:
        ordering = ['screen', 'row_identifier', 'seat_number']
        constraints = [
            models.UniqueConstraint(
                fields=['screen', 'row_identifier', 'seat_number'],
                name='unique_seat_identifier_per_screen',
            ),
            models.CheckConstraint(
                condition=Q(seat_number__gt=0),
                name='seat_number_positive',
            ),
        ]

    def __str__(self):
        return f'{self.screen} - {self.row_identifier}{self.seat_number}'


class Show(models.Model):
    movie = models.ForeignKey(
        Movie,
        on_delete=models.PROTECT,
        related_name='shows',
    )
    screen = models.ForeignKey(
        Screen,
        on_delete=models.PROTECT,
        related_name='shows',
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['start_time']
        indexes = [
            models.Index(fields=['screen', 'start_time'], name='show_screen_start_idx'),
            models.Index(fields=['movie', 'start_time'], name='show_movie_start_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_time__gt=models.F('start_time')),
                name='show_end_after_start',
            ),
            models.CheckConstraint(
                condition=Q(ticket_price__gte=0),
                name='show_ticket_price_nonnegative',
            ),
        ]

    def __str__(self):
        return f'{self.movie.title} at {self.screen} ({self.start_time:%Y-%m-%d %H:%M})'
