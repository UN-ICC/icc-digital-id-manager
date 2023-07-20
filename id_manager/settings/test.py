from .base import *

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

ROOT_DIR = Path(__file__).resolve(strict=True).parent.parent.parent
SITE_URL = "http://test.com"

ACA_PY_WEBHOOKS_API_KEY = "1234"

ORGANIZATION = "ICC_TEST"
ICC_ID_MANAGER_URL = "http://test-icc-id-manager.un-chain.org"
ICC_ID_MANAGER_AUTH_TOKEN = "auth-token"

ACA_PY_URL = "aca.py.url"
ACA_PY_TRANSPORT_URL = "aca.py.transport.url"

DEFAULT_EMAIL_FROM = "test@test"
EMAIL_HOST = ""
EMAIL_PORT = 25
EMAIL_USE_TLS = False
EMAIL_BACKEND = "post_office.EmailBackend"

SEND_EMAILS = True
