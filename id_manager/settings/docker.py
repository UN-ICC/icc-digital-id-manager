import os

from id_manager.settings.base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY")

DEBUG = os.environ.get("DEBUG", True)

ROOT_DIR = Path(__file__).resolve(strict=True).parent.parent.parent

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": os.environ.get("LOCATION", "default"),
    }
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "id_manager"),
        "USER": os.environ.get("DB_USER", "id_manager"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "change_me"),
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DB_PORT", 5432),
    }
}

ORGANIZATION = os.environ.get("ORGANIZATION", "UNOG")
SITE_URL = os.environ.get("SITE_URL")
STATIC_SERVER_URL = SITE_URL

STATICFILES_DIRS = [os.path.join(ROOT_DIR, "assets")]

# ACA_PY
ACA_PY_BASE_URL = os.environ.get("ACA_PY_BASE_URL")
ACAPY_ADMIN_PORT = os.environ.get("ACAPY_ADMIN_PORT", 4001)
ACAPY_TRANSPORT_PORT = os.environ.get("ACAPY_TRANSPORT_PORT", 8100)
ACA_PY_URL = os.environ.get("ACA_PY_URL", f"https://{ACA_PY_BASE_URL}:{ACAPY_ADMIN_PORT}")
ACA_PY_TRANSPORT_URL = os.environ.get(
    "ACA_PY_TRANSPORT_URL", f"https://{ACA_PY_BASE_URL}:{ACAPY_TRANSPORT_PORT}"
)


# EMAIL
SEND_EMAILS = os.environ.get("SEND_EMAILS", True)
DEFAULT_EMAIL_FROM = os.environ.get("DEFAULT_EMAIL_FROM", "admin@un-chain.org")
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "post_office.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtphub.unicc.org")
EMAIL_PORT = os.environ.get("EMAIL_PORT", 25)
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", False)

AWS_SES_REGION_NAME = os.environ.get("AWS_SES_REGION_NAME")
AWS_SES_REGION_ENDPOINT = os.environ.get("AWS_SES_REGION_ENDPOINT")

# ICC ID Manager
ICC_ID_MANAGER_URL = os.environ.get("ICC_ID_MANAGER_URL")
ICC_ID_MANAGER_AUTH_TOKEN = os.environ.get("ICC_ID_MANAGER_AUTH_TOKEN")
