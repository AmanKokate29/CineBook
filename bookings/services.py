import re

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import ActiveSeatClaim, BookedSeat, Booking
from theatres.models import Seat, Show


class BookingRequestError(Exception):
    pass


class BookingConflict(BookingRequestError):
    pass


def create_booking(*, user, show_id, submitted_seat_ids):
    if not user.is_authenticated:
        raise BookingRequestError('Sign in before booking seats.')

    if not submitted_seat_ids:
        raise BookingRequestError('Select at least one available seat.')
    if any(
        not isinstance(seat_id, str)
        or not re.fullmatch(r'[1-9][0-9]*', seat_id)
        for seat_id in submitted_seat_ids
    ):
        raise BookingRequestError('One or more seat selections are invalid.')
    if len(submitted_seat_ids) != len(set(submitted_seat_ids)):
        raise BookingRequestError('Duplicate seat selections are not allowed.')

    seat_ids = [int(seat_id) for seat_id in submitted_seat_ids]
    if len(seat_ids) != len(set(seat_ids)):
        raise BookingRequestError('Duplicate seat selections are not allowed.')

    try:
        with transaction.atomic():
            try:
                show = Show.objects.select_for_update().get(
                    pk=show_id,
                    is_active=True,
                    movie__is_active=True,
                    start_time__gt=timezone.now(),
                )
            except Show.DoesNotExist as exc:
                raise BookingRequestError(
                    'This show is no longer available to book.'
                ) from exc

            seats = list(
                Seat.objects.select_for_update()
                .filter(pk__in=seat_ids, screen_id=show.screen_id)
                .order_by('pk')
            )
            if len(seats) != len(seat_ids):
                raise BookingRequestError(
                    'One or more selected seats are invalid or do not belong '
                    'to this show’s screen.'
                )

            unavailable_ids = set(
                ActiveSeatClaim.objects.filter(
                    show_id=show.pk,
                    seat_id__in=seat_ids,
                ).values_list('seat_id', flat=True)
            )
            if unavailable_ids:
                raise BookingConflict(
                    'One or more selected seats are no longer available. '
                    'Please choose different seats.'
                )

            total_amount = show.ticket_price * len(seats)
            booking = Booking.objects.create(
                user=user,
                show=show,
                status=Booking.Status.CONFIRMED,
                total_amount=total_amount,
            )
            for seat in seats:
                booked_seat = BookedSeat.objects.create(
                    booking=booking,
                    show=show,
                    seat=seat,
                    price_paid=show.ticket_price,
                    status=BookedSeat.Status.ACTIVE,
                )
                ActiveSeatClaim.objects.create(
                    booked_seat=booked_seat,
                    show=show,
                    seat=seat,
                )

            return booking
    except IntegrityError as exc:
        if _is_duplicate_key_error(exc):
            raise BookingConflict(
                'A selected seat was just booked. Please choose different seats.'
            ) from exc
        raise


def _is_duplicate_key_error(exc):
    cause = exc.__cause__
    error_code = cause.args[0] if cause and cause.args else None
    message = str(cause) if cause else str(exc)
    return (
        error_code in (1062, 1555, 2067)
        and 'unique_active_claim_per_show_seat' in message
    )
