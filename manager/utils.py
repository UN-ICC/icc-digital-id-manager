import hashlib
import os
from typing import Optional

import qrcode
import structlog as logging
from django.conf import settings
from django.templatetags.static import static
from post_office import mail

LOGGER = logging.getLogger(__name__)


def anonymize(word: str, chars_shown=2, char_replacement="*"):
    word_length = len(word)
    if word_length <= chars_shown:
        return word
    return word[:chars_shown] + (word_length - chars_shown) * char_replacement


def anonymize_values(data: dict, chars_shown=2, char_replacement="*"):
    return {anonymize(value, chars_shown, char_replacement) for key, value in data.items()}


def generate_asset_url(filename: str) -> str:
    return f"{settings.STATIC_SERVER_URL}{static(filename)}"


class Assets:
    UN_LOGO = generate_asset_url("un_logo.png")
    IOS_APP_STORE_LOGO = generate_asset_url("app_store_logo.png")
    GOOGLE_PLAY_LOGO = generate_asset_url("google_play_logo.png")


class EmailHelper:
    @staticmethod
    def send(to, **kwargs):
        context = kwargs.pop("context", {})
        context["logo_url"] = Assets.UN_LOGO
        context["app_store_logo_url"] = Assets.IOS_APP_STORE_LOGO
        context["google_play_logo_url"] = Assets.GOOGLE_PLAY_LOGO
        sender = settings.DEFAULT_EMAIL_FROM

        if isinstance(to, str):
            to = (to,)

        if not settings.SEND_EMAILS:
            LOGGER.info(f"EmailHelper: emails disabled: {to}")
            return

        if not sender:
            LOGGER.info(f"EmailHelper: no sender provided: {to}")
            return

        for to_addr in to:
            LOGGER.info(f"EmailHelper: sending email to: {to_addr}")
            EmailHelper._send_one(
                to_addr,
                sender=sender,
                context=context,
                priority="now",
                **kwargs,
            )
            LOGGER.info(f"EmailHelper: email sent to: {to_addr}")

    @staticmethod
    def _send_one(to: str, **kwargs):
        try:
            mail.send(to, **kwargs)
        except Exception as e:
            LOGGER.error(f"EmailHelper: _send_one: {e}")


def get_credential_crafter_class(credential_definition_id: str):
    try:
        custom_crafter_name = settings.CREDENTIAL_CRAFTERS[credential_definition_id]
        path_components = custom_crafter_name.split(".")
        class_name = path_components[-1]
        crafter_class = getattr(
            __import__(".".join(path_components[:-1]), fromlist=[class_name]),
            class_name,
        )
    except Exception:
        from credential_crafters.base import CredentialCrafter as crafter_class

    return crafter_class


class QRCodeHandler:
    @classmethod
    def text_to_qr(cls, data: str, size: Optional[int] = 1) -> str:
        qr = qrcode.QRCode(version=size)
        qr.add_data(data)
        img = qr.make_image()
        full_image_path = cls.__full_image_path(data)
        img.save(full_image_path)
        short_path = "/".join(full_image_path.split("/")[-2:])
        return short_path

    @classmethod
    def __full_image_path(cls, file_name: str) -> str:
        suffix = ".png"
        hashed_file_name = hashlib.md5(file_name.encode()).hexdigest()
        return f"{os.path.join(settings.ROOT_DIR, 'assets', 'qr_codes', hashed_file_name + suffix)}"
