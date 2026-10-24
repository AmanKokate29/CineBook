from django.contrib import admin

from .models import ActiveSeatClaim, BookedSeat, Booking


class BookedSeatInline(admin.TabularInline):
    model = BookedSeat
    fields = ('show', 'seat', 'price_paid', 'status', 'created_at')
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('reference', 'user', 'show', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'show__movie', 'show__screen__theatre__city')
    search_fields = ('reference', 'user__username', 'show__movie__title')
    ordering = ('-created_at',)
    list_select_related = (
        'user',
        'show',
        'show__movie',
        'show__screen',
        'show__screen__theatre',
    )
    list_per_page = 50
    readonly_fields = ('reference', 'user', 'show', 'status', 'total_amount', 'created_at')
    fields = ('reference', 'user', 'show', 'status', 'total_amount', 'created_at')
    inlines = (BookedSeatInline,)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BookedSeat)
class BookedSeatAdmin(admin.ModelAdmin):
    list_display = ('booking', 'show', 'seat', 'price_paid', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'show__movie', 'show__screen__theatre')
    search_fields = ('booking__reference', 'seat__row_identifier', 'show__movie__title')
    ordering = ('-created_at',)
    list_select_related = (
        'booking',
        'booking__user',
        'show',
        'show__movie',
        'seat',
        'seat__screen',
        'seat__screen__theatre',
    )
    list_per_page = 100
    readonly_fields = ('booking', 'show', 'seat', 'price_paid', 'status', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ActiveSeatClaim)
class ActiveSeatClaimAdmin(admin.ModelAdmin):
    list_display = ('show', 'seat', 'booked_seat')
    list_filter = ('show__movie', 'show__screen__theatre')
    search_fields = ('show__movie__title', 'seat__row_identifier', 'booked_seat__booking__reference')
    ordering = ('show__start_time', 'seat__screen__name', 'seat__row_identifier', 'seat__seat_number')
    list_select_related = (
        'show',
        'show__movie',
        'show__screen',
        'seat',
        'seat__screen',
        'booked_seat',
        'booked_seat__booking',
    )
    readonly_fields = ('booked_seat', 'show', 'seat')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
