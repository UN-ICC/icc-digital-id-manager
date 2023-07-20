import os

from id_manager.settings.base import *

ALLOWED_HOSTS = ["*"]

DEBUG = True

ROOT_DIR = Path(__file__).resolve(strict=True).parent.parent.parent

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "default",
    }
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT"),
    }
}

ACA_PY_URL = "http://0.0.0.0:4002"
ACA_PY_TRANSPORT_URL = "http://0.0.0.0:8002"
ACA_PY_AUTH_TOKEN = ""

SITE_URL = "http://localhost:8082"
POLL_INTERVAL = 5000
POLL_MAX_TRIES = 12

EMAIL_HOST = os.getenv("EMAIL_HOST")

STATIC_SERVER_URL = SITE_URL
STATICFILES_DIRS = [os.path.join(ROOT_DIR, "assets")]
