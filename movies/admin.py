from django.contrib import admin

from .models import Movie


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'genre',
        'language',
        'duration',
        'release_date',
        'is_active',
    )
    list_filter = ('is_active', 'genre', 'language', 'release_date')
    search_fields = ('title', 'description', 'genre', 'language')
    ordering = ('title',)
    list_per_page = 50
    readonly_fields = ('poster_preview',)
    fieldsets = (
        (None, {'fields': ('title', 'description', 'genre', 'language')}),
        ('Release', {'fields': ('duration', 'release_date', 'poster', 'poster_preview')}),
        ('Availability', {'fields': ('is_active',)}),
    )

    @admin.display(description='Current poster')
    def poster_preview(self, obj):
        if obj and obj.poster:
            return obj.poster.url
        return 'No poster uploaded'
