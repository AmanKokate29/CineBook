from django.db import models
from django.db.models import Q


class Movie(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    genre = models.CharField(max_length=100)
    duration = models.PositiveSmallIntegerField(help_text='Duration in minutes')
    language = models.CharField(max_length=100)
    release_date = models.DateField()
    poster = models.ImageField(upload_to='movie_posters/', blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['title']
        indexes = [
            models.Index(fields=['is_active', 'title'], name='movie_active_title_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(duration__gt=0),
                name='movie_duration_positive',
            ),
        ]

    def __str__(self):
        return self.title
