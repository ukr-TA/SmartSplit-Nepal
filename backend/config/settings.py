"""
Django settings for the SmartSplit Nepal backend.

All sensitive / machine-specific values are read from environment variables,
which are loaded from the `backend/.env` file (see `.env.example`).
"""

import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load variables from backend/.env into the environment
load_dotenv(BASE_DIR / ".env")


def env(name, default=None, required=False):
    value = os.environ.get(name, default)
    if required and not value:
        raise ImproperlyConfigured(
            f"Missing environment variable '{name}'. "
            "Did you copy .env.example to .env and fill it in?"
        )
    return value


def env_bool(name, default=False):
    return str(env(name, str(default))).strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


# --------------------------------------------------------------------------
# Core
# --------------------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY", required=True)
DEBUG = env_bool("DEBUG", False)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    # SmartSplit apps
    "users",
    "groups",
    "expenses",
    "settlements",
    "notifications",
    "insights",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # must be as high as possible
    "django.middleware.security.SecurityMiddleware",
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

WSGI_APPLICATION = "config.wsgi.application"

# --------------------------------------------------------------------------
# Database (PostgreSQL)
# --------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DATABASE_NAME", "smartsplit"),
        "USER": env("DATABASE_USER", "postgres"),
        "PASSWORD": env("DATABASE_PASSWORD", ""),
        "HOST": env("DATABASE_HOST", "localhost"),
        "PORT": env("DATABASE_PORT", "5432"),
    }
}

# --------------------------------------------------------------------------
# Authentication
# --------------------------------------------------------------------------
# Custom user model (email login + phone number). Set up from the very first
# migration because Django cannot easily switch user models later.
AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --------------------------------------------------------------------------
# Django REST Framework
# --------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "60/minute"},
    "COERCE_DECIMAL_TO_STRING": True,
    "DATETIME_FORMAT": "iso-8601",
}

# --------------------------------------------------------------------------
# CORS (lets the React dev server call this API)
# --------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
)

# --------------------------------------------------------------------------
# Internationalisation — Nepal first
# --------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kathmandu"
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------------
# Static & media files (receipts, profile pictures)
# --------------------------------------------------------------------------
STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

if "test" in sys.argv:  # keep test uploads out of the real media folder
    import tempfile

    MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="smartsplit-test-media-"))

# Upload limits (receipts up to 5 MB, profile pictures up to 3 MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------------------
# Machine learning models
# --------------------------------------------------------------------------
# Artefacts exported by ml/notebooks/smartsplit_ml.ipynb. If the folder or the files are
# missing the API still works: category suggestions fall back to keyword matching and the
# spending forecast falls back to the average of the last three months.
ML_MODELS_DIR = Path(env("ML_MODELS_DIR", str(BASE_DIR.parent / "ml" / "models")))

# --------------------------------------------------------------------------
# Payments (eSewa / Khalti)
# --------------------------------------------------------------------------
# Where the React app runs — gateways send the user back here after paying.
FRONTEND_URL = env("FRONTEND_URL", "http://localhost:5173").rstrip("/")

# eSewa ePay v2 TEST environment. These are eSewa's public test credentials
# (published in eSewa's developer docs) — no real money is involved.
ESEWA_ENABLED = env_bool("ESEWA_ENABLED", True)
ESEWA_PRODUCT_CODE = env("ESEWA_PRODUCT_CODE", "EPAYTEST")
ESEWA_SECRET_KEY = env("ESEWA_SECRET_KEY", "8gBm/:&EnhH.1/q")
ESEWA_FORM_URL = env("ESEWA_FORM_URL", "https://rc-epay.esewa.com.np/api/epay/main/v2/form")
ESEWA_STATUS_URL = env("ESEWA_STATUS_URL", "https://rc.esewa.com.np/api/epay/transaction/status/")

# Khalti KPG-2 sandbox. Leave the key empty to use the in-app simulation only.
# Get a test key at https://test-admin.khalti.com (see SETUP.md).
KHALTI_SECRET_KEY = env("KHALTI_SECRET_KEY", "")
KHALTI_BASE_URL = env("KHALTI_BASE_URL", "https://dev.khalti.com/api/v2/")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"settlements": {"handlers": ["console"], "level": "INFO"}},
}
