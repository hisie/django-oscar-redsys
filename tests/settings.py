"""Minimal Django settings to run this package's own test suite.

Not django-oscar's full settings module — this package doesn't need Oscar
installed to test the crypto/facade/views, only Django itself, so oscar
isn't a listed app here (kept as a light, fast-running test suite).
"""

from __future__ import annotations

SECRET_KEY = "not-a-real-secret-key-only-used-to-run-this-packages-tests"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.messages",
    "oscar_redsys",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "tests.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

USE_TZ = True

# Test-only Redsys credentials — the values Redsys itself publishes for
# its shared sandbox merchant (redirection manual, section 5).
REDSYS_MERCHANT_CODE = "999008881"
REDSYS_TERMINAL = "1"
REDSYS_SECRET_KEY = "sq7HjrUOBfKmC576"
REDSYS_SANDBOX = True
REDSYS_MERCHANT_URL = "https://example.com/redsys/notify/"
REDSYS_URL_OK = "https://example.com/redsys/return/?ok=1"
REDSYS_URL_KO = "https://example.com/redsys/return/?ok=0"
