"""Django settings for the Internal Tracker (Trackroom).

Secrets and machine-specific values are never written in this file. They
come from environment variables (Heroku config vars in production) or,
for local development only, from the git-ignored ``config/env.py``.
"""

from importlib import import_module
import os
import sys
from pathlib import Path

import dj_database_url
from django.contrib.messages import constants as message_constants
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

try:
    # Local-only values live in config/env.py, which .gitignore excludes.
    local_env = import_module("config.env")
except ModuleNotFoundError as error:
    if error.name != "config.env":
        raise
    local_env = None


def setting(name, default):
    """Read a setting from the environment, then env.py, then default."""
    return os.environ.get(name, getattr(local_env, name, default))


def as_bool(value):
    """Turn "True", "1", "yes" or a real boolean into True or False."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def as_list(value):
    """Split a comma-separated string into a clean list."""
    return [item.strip() for item in str(value).split(",") if item.strip()]


INSECURE_DEV_KEY = "django-insecure-local-development-only"
SECRET_KEY = setting("SECRET_KEY", INSECURE_DEV_KEY)

# DEBUG is off unless it is switched on, so a missing value is safe.
DEBUG = as_bool(setting("DEBUG", False))

ALLOWED_HOSTS = as_list(setting("ALLOWED_HOSTS", "127.0.0.1,localhost"))
CSRF_TRUSTED_ORIGINS = as_list(setting("CSRF_TRUSTED_ORIGINS", ""))

# The test runner is detected so tests never need production secrets.
TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"

if not DEBUG and not TESTING:
    if SECRET_KEY == INSECURE_DEV_KEY:
        raise ImproperlyConfigured(
            "Set a unique SECRET_KEY environment variable for production."
        )
    if not ALLOWED_HOSTS:
        raise ImproperlyConfigured(
            "Set ALLOWED_HOSTS to your Heroku app hostname."
        )

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "equipment",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "equipment.context_processors.manager_badges",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Heroku supplies DATABASE_URL (PostgreSQL). Without it, a local choice of
# SQLite (the default) or a local PostgreSQL server is read from env.py.
database_url = setting("DATABASE_URL", "")
database_engine = str(setting("DATABASE_ENGINE", "sqlite")).lower()
if database_url:
    DATABASES = {
        "default": dj_database_url.parse(
            database_url,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=database_url.startswith("postgres") and not DEBUG,
        )
    }
elif database_engine in {"postgres", "postgresql"}:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": setting("DATABASE_NAME", "internal_tracker"),
            "USER": setting("DATABASE_USER", "postgres"),
            "PASSWORD": setting("DATABASE_PASSWORD", ""),
            "HOST": setting("DATABASE_HOST", "127.0.0.1"),
            "PORT": setting("DATABASE_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation."
        "UserAttributeSimilarityValidator",
    },
    {"NAME": "django.contrib.auth.password_validation."
     "MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation."
     "CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation."
     "NumericPasswordValidator"},
]

if TESTING:
    # A fast hasher keeps the test suite quick. Never used outside tests.
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Hashed, compressed static files in production. Plain storage while
# developing or testing, because tests never run collectstatic.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG or TESTING
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}

# Match Django message levels to the CSS classes used in base.html.
MESSAGE_TAGS = {message_constants.ERROR: "error"}

# Heroku terminates HTTPS at its router and forwards the original scheme.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
if not DEBUG and not TESTING:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31_536_000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# Send errors to the Heroku log so live problems can be traced.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"django": {"handlers": ["console"], "level": "WARNING"}},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
