import os.path
from unittest.mock import call

import pytest
from django.conf import settings
from django.test import override_settings
from post_office import mail

from credential_crafters.base import CredentialCrafter
from manager.utils import (
    Assets,
    EmailHelper,
    QRCodeHandler,
    anonymize,
    anonymize_values,
    generate_asset_url,
    get_credential_crafter_class,
)


def test_anonymize():
    word = "abracadabra"
    assert anonymize(word) == "ab*********"
    assert anonymize(word, 3, "-") == "abr--------"
    assert anonymize(word, len(word)) == word
    assert anonymize(word, len(word) + 1) == word


def test_anonymize_values():
    to_be_anonymized = {"id": "Ada Lovelace", "credential": "abracadabra"}
    anonymized_default = {"Ad**********", "ab*********"}
    anonymized_special = {"Ada --------", "abra-------"}
    assert anonymize_values(to_be_anonymized) == anonymized_default
    assert anonymize_values(to_be_anonymized, 4, "-") == anonymized_special


@override_settings(STATIC_SERVER_URL="http://127.0.0.1")
def test_generate_asset_url():
    filename = "test_filename.txt"
    assert generate_asset_url(filename) == "http://127.0.0.1/static/test_filename.txt"


class TestAssets:
    def test_logo_urls(self):
        assert Assets.UN_LOGO == "/static/un_logo.png"
        assert Assets.IOS_APP_STORE_LOGO == "/static/app_store_logo.png"
        assert Assets.GOOGLE_PLAY_LOGO == "/static/google_play_logo.png"


@pytest.mark.django_db
class TestEmailHelper:
    @staticmethod
    def send_test_emails():
        EmailHelper.send(
            ["some@emails.com", "some_other@emails.com"],
            template="invitation",
            context={"some_parameter": "some_value"},
        )

    @override_settings(SEND_EMAILS=True, DEFAULT_EMAIL_FROM="test@email.org")
    def test_send(self, mocker):
        post_office_mail = mocker.patch.object(mail, "send")
        self.send_test_emails()

        expected_params = {
            "sender": "test@email.org",
            "template": "invitation",
            "context": {
                "some_parameter": "some_value",
                "logo_url": Assets.UN_LOGO,
                "app_store_logo_url": Assets.IOS_APP_STORE_LOGO,
                "google_play_logo_url": Assets.GOOGLE_PLAY_LOGO,
            },
            "priority": "now",
        }

        post_office_mail.assert_has_calls(
            [
                call("some@emails.com", **expected_params),
                call("some_other@emails.com", **expected_params),
            ],
            any_order=True,
        )

    @override_settings(SEND_EMAILS=True, DEFAULT_EMAIL_FROM=None)
    def test_send_without_default_sender(self, mocker):
        post_office_mail = mocker.patch.object(mail, "send")
        self.send_test_emails()
        post_office_mail.assert_not_called()

    @override_settings(SEND_EMAILS=None)
    def test_send_without_send_email_settings(self, mocker):
        post_office_mail = mocker.patch.object(mail, "send")
        self.send_test_emails()
        post_office_mail.assert_not_called()


@override_settings(CREDENTIAL_CRAFTERS=["module.CrafterClass"])
def test_get_credential_crafter_class():
    assert get_credential_crafter_class(0) == CredentialCrafter


@override_settings(CREDENTIAL_CRAFTERS=["module.secondmodule.TestCrafterClass"])
def test_get_credential_crafter_class_does_not_exist():
    assert get_credential_crafter_class(0) == CredentialCrafter


@override_settings(CREDENTIAL_CRAFTERS=["module.secondmodule.TestCrafterClass"])
def test_get_credential_crafter_class_does_out_of_bounds():
    assert get_credential_crafter_class(1) == CredentialCrafter


@pytest.mark.django_db
class TestQRCodeHandler:
    def test_text_to_qr_creates_qr_image(self):
        data = "goodreads"
        qr_image_path = QRCodeHandler.text_to_qr(data)

        image_path = os.path.join(settings.ROOT_DIR, "assets", qr_image_path)
        assert os.path.isfile(image_path)
        os.remove(image_path)
