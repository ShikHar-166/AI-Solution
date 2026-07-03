import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


# SECURITY
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    os.getenv(
        "SECRET_KEY",
        "django-insecure-ai-solution-development-key-change-in-production"
    )
)

DEBUG = os.getenv(
    "DJANGO_DEBUG",
    os.getenv("DEBUG", "True")
).lower() == "true"


# ALLOWED HOSTS
allowed_hosts = os.getenv(
    "DJANGO_ALLOWED_HOSTS",
    os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost")
)

ALLOWED_HOSTS = [
    host.strip()
    for host in allowed_hosts.split(",")
    if host.strip()
]


# CSRF TRUSTED ORIGINS
csrf_trusted_origins = os.getenv(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    os.getenv("CSRF_TRUSTED_ORIGINS", "")
)

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in csrf_trusted_origins.split(",")
    if origin.strip()
]


# APPLICATIONS
INSTALLED_APPS = [
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "main",
]


# MIDDLEWARE
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "core.urls"


# TEMPLATES
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"


# DATABASE
# This project uses MongoDB directly through PyMongo.
# Django relational database is kept only as a safe default.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# INTERNATIONALIZATION
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# STATIC FILES
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    }
}


# SESSION AND CSRF COOKIES
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# Render / HTTPS proxy support
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
