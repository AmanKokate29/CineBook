import uuid

from django.conf import settings
from django.db import models, transaction
from django.db.models import Q

from theatres.models import Seat, Show


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        CANCELLED = 'cancelled', 'Cancelled'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='bookings',
    )
    show = models.ForeignKey(
        Show,
        on_delete=models.PROTECT,
        related_name='bookings',
    )
    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at'], name='booking_user_created_idx'),
            models.Index(fields=['show', 'status'], name='booking_show_status_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(total_amount__gte=0),
                name='booking_total_nonnegative',
            ),
        ]

    def __str__(self):
        return f'Booking {self.reference} ({self.get_status_display()})'

    def cancel(self):
        if self.pk is None:
            raise ValueError('A booking must be saved before it can be cancelled.')

        with transaction.atomic():
            booking = Booking.objects.select_for_update().get(pk=self.pk)
            if booking.status != self.Status.CANCELLED:
                BookedSeat.objects.filter(
                    booking=booking,
                    status=BookedSeat.Status.ACTIVE,
                ).update(status=BookedSeat.Status.RELEASED)
                ActiveSeatClaim.objects.filter(booked_seat__booking=booking).delete()
                booking.status = self.Status.CANCELLED
                booking.save(update_fields=['status'])

        self.status = self.Status.CANCELLED


class BookedSeat(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        RELEASED = 'released', 'Released'

    booking = models.ForeignKey(
        Booking,
        on_delete=models.PROTECT,
        related_name='booked_seats',
    )
    show = models.ForeignKey(
        Show,
        on_delete=models.PROTECT,
        related_name='booked_seats',
    )
    seat = models.ForeignKey(
        Seat,
        on_delete=models.PROTECT,
        related_name='booking_history',
    )
    price_paid = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['booking', 'status'], name='booked_seat_status_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(price_paid__gte=0),
                name='booked_seat_price_nonnegative',
            ),
        ]

    def __str__(self):
        return f'{self.seat} for {self.show} ({self.get_status_display()})'


class ActiveSeatClaim(models.Model):
    booked_seat = models.OneToOneField(
        BookedSeat,
        on_delete=models.PROTECT,
        related_name='active_claim',
    )
    show = models.ForeignKey(
        Show,
        on_delete=models.PROTECT,
        related_name='active_seat_claims',
    )
    seat = models.ForeignKey(
        Seat,
        on_delete=models.PROTECT,
        related_name='active_show_claims',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['show', 'seat'],
                name='unique_active_claim_per_show_seat',
            ),
        ]

    def __str__(self):
        return f'{self.seat} claimed for {self.show}'
