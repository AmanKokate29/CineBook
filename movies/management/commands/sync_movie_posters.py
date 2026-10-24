import json
import os
import re
import unicodedata
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from PIL import Image, UnidentifiedImageError

from movies.models import Movie


TMDB_API_BASE = 'https://api.themoviedb.org/3'
TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p/w500'
REQUEST_TIMEOUT_SECONDS = 15
MAX_POSTER_BYTES = 8 * 1024 * 1024
POSTER_PATH_PATTERN = re.compile(r'^/[A-Za-z0-9_-]+\.(?:jpe?g|png|webp)$', re.I)


def _normalize_title(value):
    normalized = unicodedata.normalize('NFKD', value).casefold()
    return ''.join(character for character in normalized if character.isalnum())


def _release_year(value):
    match = re.match(r'^(\d{4})-', value or '')
    return int(match.group(1)) if match else None


def _tmdb_request(url, token):
    request = Request(
        url,
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer ' + token,
            'User-Agent': 'CineBook poster importer',
        },
    )
    try:
        return urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS)
    except HTTPError as error:
        if error.code in (401, 403):
            raise CommandError(
                'TMDb rejected the API token. Check TMDB_API_READ_ACCESS_TOKEN.'
            ) from error
        raise CommandError(
            f'TMDb request failed with HTTP {error.code}.'
        ) from error
    except (URLError, TimeoutError) as error:
        raise CommandError(f'Could not reach TMDb: {error}.') from error


def _search_movie(title, year, token):
    query = urlencode({'query': title})
    with _tmdb_request(f'{TMDB_API_BASE}/search/movie?{query}', token) as response:
        try:
            payload = json.loads(response.read())
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise CommandError('TMDb returned an invalid search response.') from error

    if not isinstance(payload, dict) or not isinstance(payload.get('results'), list):
        raise CommandError('TMDb returned an unexpected search response.')

    normalized_title = _normalize_title(title)
    matches = []
    for result in payload['results']:
        if not isinstance(result, dict):
            continue
        titles = (
            result.get('title', ''),
            result.get('original_title', ''),
        )
        if not any(
            isinstance(candidate_title, str)
            and _normalize_title(candidate_title) == normalized_title
            for candidate_title in titles
        ):
            continue

        result_year = _release_year(result.get('release_date', ''))
        if result_year is None or abs(result_year - year) > 1:
            continue
        poster_path = result.get('poster_path')
        if not isinstance(poster_path, str) or not POSTER_PATH_PATTERN.fullmatch(
            poster_path
        ):
            continue

        matches.append((abs(result_year - year), result))

    if not matches:
        return None

    matches.sort(key=lambda match: match[0])
    closest_year_delta = matches[0][0]
    closest_matches = [
        result
        for year_delta, result in matches
        if year_delta == closest_year_delta
    ]
    if len(closest_matches) != 1:
        return None
    return closest_matches[0]


def _download_poster(poster_path, token):
    url = f'{TMDB_IMAGE_BASE}{poster_path}'
    with _tmdb_request(url, token) as response:
        content_type = response.headers.get('Content-Type', '').split(';', 1)[0]
        if content_type not in {'image/jpeg', 'image/png', 'image/webp'}:
            raise CommandError(
                f'TMDb returned an unsupported image type for {poster_path}.'
            )
        content = response.read(MAX_POSTER_BYTES + 1)

    if len(content) > MAX_POSTER_BYTES:
        size_limit_mb = MAX_POSTER_BYTES // 1024 // 1024
        raise CommandError(f'TMDb poster exceeds the {size_limit_mb} MB limit.')

    try:
        with Image.open(BytesIO(content)) as image:
            image_extensions = {
                'JPEG': 'jpg',
                'PNG': 'png',
                'WEBP': 'webp',
            }
            extension = image_extensions.get(image.format)
            if not extension:
                raise CommandError('TMDb returned an unsupported poster format.')
            image.verify()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as error:
        raise CommandError('TMDb returned an invalid poster image.') from error

    return content, extension


class Command(BaseCommand):
    help = 'Download verified movie posters from TMDb for movies without posters.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Search TMDb and report matches without downloading posters.',
        )

    def handle(self, *args, **options):
        token = os.environ.get('TMDB_API_READ_ACCESS_TOKEN', '').strip()
        if not token:
            raise CommandError(
                'Set TMDB_API_READ_ACCESS_TOKEN in your local .env before running '
                'this command.'
            )

        movies = Movie.objects.filter(poster='').order_by('pk')
        if not movies.exists():
            self.stdout.write(self.style.SUCCESS('All movies already have posters.'))
            return

        imported = 0
        unmatched = 0
        for movie in movies.iterator(chunk_size=50):
            match = _search_movie(
                movie.title,
                movie.release_date.year,
                token,
            )
            if match is None:
                unmatched += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'No unambiguous exact-title poster found: {movie.title} '
                        f'({movie.release_date.year})'
                    )
                )
                continue

            if options['dry_run']:
                self.stdout.write(
                    f'Would import poster: {movie.title} ({movie.release_date.year})'
                )
                continue

            content, extension = _download_poster(match['poster_path'], token)
            filename = (
                f'{movie.pk}-{slugify(movie.title)[:80] or "movie"}-tmdb.{extension}'
            )
            movie.poster.save(filename, ContentFile(content), save=False)
            movie.save(update_fields=['poster'])
            imported += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'Imported poster: {movie.title} ({movie.release_date.year})'
                )
            )

        if options['dry_run']:
            self.stdout.write(
                f'Dry run complete: {unmatched} movie(s) had no unambiguous exact match.'
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Poster sync complete: {imported} imported, '
                    f'{unmatched} unmatched.'
                )
            )
