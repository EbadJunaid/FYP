"""
Django settings for SSL_Dashboard project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------------------------------------------------------------
# 1. LOAD ENVIRONMENT VARIABLES
# -----------------------------------------------------------------------------
# Reads the .env file locally. Render will provide these variables automatically in production.
load_dotenv(os.path.join(BASE_DIR, ".env"))

# -----------------------------------------------------------------------------
# 2. SECURITY & HOSTS
# -----------------------------------------------------------------------------
# Fallback key is for local dev only. Render will provide the real one.
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-fallback-dev-key")

# DEBUG must be False in production
DEBUG = os.getenv("DEBUG", "False") == "True"

ALLOWED_HOSTS = [
    ".onrender.com",  # Required for Render
    "localhost",
    "127.0.0.1"
]

# -----------------------------------------------------------------------------
# 3. INSTALLED APPS & MIDDLEWARE
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",  # Crucial for frontend communication
    "overview",     # Your app
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware", # Optional: handles static files
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",      # MUST be near top
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "SSL_Dashboard.urls"

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

WSGI_APPLICATION = "SSL_Dashboard.wsgi.application"

# -----------------------------------------------------------------------------
# 4. DATABASES
# -----------------------------------------------------------------------------

# Django Default (Required even if using Mongo)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# MongoDB Configuration
# We check for the URI first (Atlas), then fallback to localhost
MONGO_URI = os.getenv("MONGO_URI") 
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "pkdomains")

if not MONGO_URI:
    MONGODB_HOST = os.getenv("MONGODB_HOST", "localhost")
    MONGODB_PORT = int(os.getenv("MONGODB_PORT", "27017"))

# -----------------------------------------------------------------------------
# 5. CORS (Frontend Connection)
# -----------------------------------------------------------------------------
# Split the env string into a list. Default to localhost for dev.
allowed_origins = os.getenv("CORS_ORIGIN_WHITELIST", "http://localhost:3000")
CORS_ALLOWED_ORIGINS = allowed_origins.split(",")

CORS_ALLOW_CREDENTIALS = True

# -----------------------------------------------------------------------------
# 6. PASSWORD VALIDATION & I18N
# -----------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"