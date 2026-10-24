# CineBook

CineBook is a Django movie ticket booking portal. Visitors can browse and search
the movie catalogue, view upcoming showtimes, and select seats. Authenticated
users can create bookings, review their booking history, and cancel eligible
bookings.

## Project objectives

- Provide a simple movie discovery and ticket booking experience.
- Model theatres, screens, seats, shows, bookings, and reservations using Django
  ORM.
- Prevent simultaneous requests from claiming the same seat for the same show.
- Preserve booking and seat-price history when a booking is cancelled.
- Keep the frontend accessible and responsive using Django Templates, CSS, and
  vanilla JavaScript.

## Features

- Registration, login, logout, profile access, and protected booking pages.
- Active movie catalogue with title search, genre filtering, pagination, and
  movie details.
- Upcoming showtime browsing by movie and date, grouped by theatre and screen.
- Database-backed seat selection with availability checked again on submission.
- Atomic booking creation with server-calculated prices and database-enforced
  unique active seat claims.
- Booking confirmation (no payment is processed), booking history, and
  owner-protected booking details.
- Cancellation of pending or confirmed bookings until the show starts.
  Cancellation releases seats while retaining the booking and seat-price
  history.
- Django Admin management for catalogue and venue data; booking records are
  read-only in the admin.

## Technology stack

- Python 3.14.5 (current development environment; Django 5.2 supports Python
  3.10 and later)
- Django 5.2.18
- MySQL 8.0.41 in the current development environment
- `mysqlclient` 2.3.0
- `python-dotenv` 1.2.4
- Pillow 13.0.0 for image fields
- Django Templates, HTML5, CSS3, and vanilla JavaScript

Python dependencies and versions are pinned in [`requirements.txt`](requirements.txt).

## Architecture overview

The project uses Django's standard project-and-app structure. `config` contains
the project settings and root URL configuration. Each application owns its
domain models, views, URLs, admin configuration, and tests. Django Templates
render server-side pages; shared layout and styles are in `templates/base.html`
and `static/`.

| Application | Responsibility |
| --- | --- |
| `accounts` | Registration, login, logout, and profile pages using Django authentication |
| `movies` | Movie catalogue, movie details, search, and genre filtering |
| `theatres` | Theatres, screens, seats, shows, showtime browsing, and seat selection |
| `bookings` | Booking creation, active seat claims, booking history, cancellation, and confirmation |
| `config` | Django settings, ASGI/WSGI entry points, and root URL routing |

### Database relationships

```text
Movie 1 ── * Show * ── 1 Screen * ── 1 Theatre
                         |
                         └── 1 * Seat

User 1 ── * Booking * ── 1 Show
                  |
                  └── 1 * BookedSeat * ── 1 Seat
                              |
                              └── 0..1 ActiveSeatClaim
                                  (unique per show and seat)
```

`ActiveSeatClaim` has a database uniqueness constraint on `(show, seat)`, so an
active claim cannot conflict with another claim for the same show and seat.
Cancelled bookings keep their `Booking` and `BookedSeat` records; their seat
history is marked released and active claims are removed.

## Screenshots

Screenshots have not yet been added to the repository. Add project screenshots
under `docs/screenshots/` and link them here when available. Suggested captures:

- Movie catalogue
- Movie showtimes
- Seat selection
- Booking confirmation
- Booking history and details

## Requirements

- Python 3.10 or later (the current project environment uses Python 3.14.5).
- MySQL Server 8.0 or later. Use InnoDB tables for transactional booking and
  row-locking behavior.
- A MySQL account permitted to create/use the application database. Running
  automated tests also requires Django's test database to be created and
  dropped.
- On Windows, if `mysqlclient` has no compatible prebuilt wheel for your
  Python setup, install the MySQL development libraries and C++ build tools
  required by `mysqlclient`.

## Local setup (Windows PowerShell)

Run commands from the repository root.

### 1. Create and activate a virtual environment

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell prevents activation, you can run the project interpreter directly
as `.\.venv\Scripts\python.exe` without changing the execution policy.

### 2. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Create the MySQL database and an application user

Connect to MySQL using an account with permission to create databases and users,
then run the following SQL. Replace the example password locally with a strong
password; do not commit it:

```sql
CREATE DATABASE cinebook_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE USER 'cinebook_app'@'127.0.0.1'
    IDENTIFIED BY 'replace-with-a-strong-local-password';

GRANT ALL PRIVILEGES ON cinebook_db.* TO 'cinebook_app'@'127.0.0.1';
```

If you use another MySQL username or host, configure the corresponding values
in `.env`. Confirm MySQL Server is running before starting Django.

### 4. Configure environment variables

The repository includes [`.env.example`](.env.example) with placeholder values.
Copy it to a local `.env` file:

```powershell
Copy-Item .env.example .env
notepad .env
```

Set values in `.env` for your local database. For example, set `DB_USER` to
`cinebook_app` and `DB_PASSWORD` to the password chosen for that MySQL user.
Keep `DJANGO_DEBUG=True` and `DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost` only for
local development. Production must set `DJANGO_DEBUG=False` and configure
`DJANGO_ALLOWED_HOSTS` to the exact hostnames serving the application.
With debug disabled, HTTPS redirects and secure session/CSRF cookies are
enabled by default. Reverse-proxy deployments may need to configure the
appropriate proxy HTTPS header or redirect behavior. Set
`DJANGO_TRUST_X_FORWARDED_PROTO=True` only when a trusted reverse proxy
overwrites `X-Forwarded-Proto` and strips untrusted client-supplied values.
Generate a Django secret key locally:

```powershell
$secret = .\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
$settings = Get-Content .env | Where-Object { $_ -notmatch '^DJANGO_SECRET_KEY=' }
Set-Content .env $settings
Add-Content .env "DJANGO_SECRET_KEY=$secret"
```

This replaces the placeholder key with a newly generated local value. The
required variables are:

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Django signing and session secret |
| `DJANGO_DEBUG` | Enables Django debug mode (`True` only for local development) |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames accepted by Django |
| `DJANGO_SECURE_SSL_REDIRECT` | Override HTTPS redirect behavior |
| `DJANGO_SESSION_COOKIE_SECURE` | Override secure session cookie behavior |
| `DJANGO_CSRF_COOKIE_SECURE` | Override secure CSRF cookie behavior |
| `DJANGO_SECURE_HSTS_SECONDS` | Enable HSTS after confirming HTTPS deployment |
| `DJANGO_TRUST_X_FORWARDED_PROTO` | Trust a reverse proxy's HTTPS protocol header |
| `TMDB_API_READ_ACCESS_TOKEN` | Optional TMDb token for importing movie posters |
| `DB_NAME` | MySQL database name (`cinebook_db` for the setup above) |
| `DB_USER` | MySQL application username |
| `DB_PASSWORD` | MySQL application password |
| `DB_HOST` | MySQL host (default in the example: `127.0.0.1`) |
| `DB_PORT` | MySQL port (default in the example: `3306`) |

`.env` is excluded from Git by [`.gitignore`](.gitignore). Never commit real
credentials or secret keys. Keep `.env.example` limited to placeholders.

### Import movie posters from TMDb

The movie catalogue supports uploaded posters in Django Admin. To import posters
for movies that do not already have one, request a TMDb API Read Access Token,
set `TMDB_API_READ_ACCESS_TOKEN` in your local `.env`, and preview matches:

```powershell
.\.venv\Scripts\python.exe manage.py sync_movie_posters --dry-run
```

The importer only accepts exact normalized title matches with a release year
within one year of the movie record. It skips ambiguous or unmatched results
and preserves posters already uploaded in Admin. After reviewing the preview,
run:

```powershell
.\.venv\Scripts\python.exe manage.py sync_movie_posters
```

Imported files are stored under `media/movie_posters/`. Restart the development
server if needed and reload the movie catalogue. Movies without a confident
match continue to use the local illustrated fallback. This product uses the
TMDB API but is not endorsed or certified by TMDB.

### 5. Apply migrations

```powershell
python manage.py migrate
```

Check migration status:

```powershell
python manage.py showmigrations
python manage.py makemigrations --check --dry-run
```

### 6. Create an administrator

```powershell
python manage.py createsuperuser
```

Use the prompts to set the local admin username, email, and password.

### 7. Run the development server

```powershell
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. The Django Admin is at
<http://127.0.0.1:8000/admin/>.

## Automated tests

Run the complete Django test suite:

```powershell
python manage.py test
```

Run tests by app:

```powershell
python manage.py test accounts
python manage.py test movies
python manage.py test theatres
python manage.py test bookings
```

Run the simultaneous booking test on its own:

```powershell
python manage.py test bookings.tests.ConcurrentBookingTests -v 2
```

The ordinary tests primarily use Django `TestCase`, which isolates each test in
a transaction. `ConcurrentBookingTests` uses `TransactionTestCase` and separate
database connections so concurrent transactions can exercise database locking.
Run that test against a database that supports `SELECT FOR UPDATE`; this
project's MySQL/InnoDB setup is the intended configuration. A database without
row-locking support may skip the test and does not demonstrate production
concurrency behavior.

The test database is created and removed by Django. The configured MySQL
account needs the privileges required for that operation. The runtime grant in
the example is intentionally limited to `cinebook_db`; automated tests also
need permission to create and drop Django's test database. For tests, use a
separate local MySQL account with the necessary test-database privileges, or
temporarily grant them to a development-only account. Do not use an elevated
test account for production.

## Project structure

```text
CineBook/
├── accounts/
│   ├── migrations/
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── bookings/
│   ├── migrations/
│   ├── tests.py
│   ├── models.py
│   ├── services.py
│   ├── urls.py
│   └── views.py
├── config/
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── movies/
│   ├── migrations/
│   ├── tests.py
│   ├── models.py
│   ├── urls.py
│   └── views.py
├── static/
│   ├── css/style.css
│   └── js/main.js
├── templates/
│   ├── accounts/
│   ├── bookings/
│   ├── movies/
│   ├── pages/
│   ├── theatres/
│   └── base.html
├── theatres/
│   ├── migrations/
│   ├── tests.py
│   ├── models.py
│   ├── urls.py
│   └── views.py
├── .env.example
├── .gitignore
├── manage.py
└── requirements.txt
```

## Security considerations

- Keep `.env` and all real credentials out of version control.
- Django's built-in authentication handles password hashing; protected booking
  pages and details are scoped to the signed-in user.
- State-changing booking, cancellation, and logout actions use POST and Django
  CSRF protection.
- Booking prices and availability are validated server-side. A database
  uniqueness constraint protects active seat claims under concurrent booking
  requests.
- **Configuration hardened:** debug now defaults to `False`,
  hostnames are environment-configured, and DB credentials are required. The
  example file enables debug only for local use. These settings are still
  **not a complete production configuration**. Before deployment, configure
  the production HTTPS/proxy setup, opt into HSTS only after confirming the
  domain is HTTPS-only, review secret management and database permissions,
  configure backups, and arrange production media/static serving.
- Uploaded poster files are stored under the configured local media directory.
  Production media storage and serving need to be configured separately.

## Known limitations

- Payment processing is not implemented; a booking confirmation does not charge
  the user.
- Cancellation is permitted only before the show starts. There is no separate
  configurable cutoff or refund workflow.
- Local development settings are not a production deployment configuration.
- Production media storage/serving and static asset deployment are not included.
- The application has no automated email notifications or external ticket
  delivery.

## Future improvements

- Integrate a payment provider with verified payment callbacks and refund
  handling.
- Define a configurable cancellation cutoff and refund policy.
- Add booking-history pagination and optional filters.
- Add email confirmations and ticket delivery.
- Configure production deployment, secure settings, media storage, monitoring,
  and backup procedures.
- Add polished project screenshots and deployment documentation.
