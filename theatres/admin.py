from django.contrib import admin

from bookings.models import BookedSeat

from .models import Screen, Seat, Show, Theatre


class ScreenInline(admin.TabularInline):
    model = Screen
    fields = ('name',)
    extra = 0
    show_change_link = True


class SeatInline(admin.TabularInline):
    model = Seat
    fields = ('row_identifier', 'seat_number', 'seat_type')
    extra = 0


class BookedSeatInline(admin.TabularInline):
    model = BookedSeat
    fields = ('booking', 'seat', 'price_paid', 'status')
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Theatre)
class TheatreAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'address')
    list_filter = ('city',)
    search_fields = ('name', 'city', 'address')
    ordering = ('city', 'name')
    inlines = (ScreenInline,)
    list_per_page = 50


@admin.register(Screen)
class ScreenAdmin(admin.ModelAdmin):
    list_display = ('name', 'theatre', 'seat_count')
    list_filter = ('theatre__city', 'theatre')
    search_fields = ('name', 'theatre__name', 'theatre__city')
    ordering = ('theatre__city', 'theatre__name', 'name')
    inlines = (SeatInline,)
    list_select_related = ('theatre',)
    list_per_page = 50

    @admin.display(description='Seats')
    def seat_count(self, obj):
        return obj.seats.count()


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ('row_identifier', 'seat_number', 'screen', 'seat_type')
    list_filter = ('seat_type', 'screen__theatre__city', 'screen__theatre', 'screen')
    search_fields = ('row_identifier', 'screen__name', 'screen__theatre__name')
    ordering = ('screen__theatre__name', 'screen__name', 'row_identifier', 'seat_number')
    list_select_related = ('screen', 'screen__theatre')
    list_per_page = 100


@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    list_display = ('movie', 'screen', 'start_time', 'end_time', 'ticket_price', 'is_active')
    list_filter = ('is_active', 'start_time', 'movie__genre', 'screen__theatre__city')
    search_fields = ('movie__title', 'screen__name', 'screen__theatre__name')
    ordering = ('start_time',)
    list_select_related = ('movie', 'screen', 'screen__theatre')
    inlines = (BookedSeatInline,)
    list_per_page = 50
