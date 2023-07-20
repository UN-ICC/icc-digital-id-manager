from unittest.mock import call

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status

from manager.handlers import ACAPy


@pytest.mark.django_db
class TestCredentialRequestAdmin:
    @pytest.fixture
    def set_up(self, mocker, api_client_admin):
        self.change_url = reverse("admin:manager_credentialrequest_changelist")

        self.revoke_mocker = mocker.patch.object(ACAPy, "send_revoke_credential", return_value={})

        self.username = "content_tester"
        self.password = "goldenstandard"
        self.user = User.objects.create_superuser(self.username, "test@example.com", self.password)
        self.client = api_client_admin

    @pytest.fixture
    def cred_request(self, credential_request, credential_offer):
        credential_offer.credential_request = credential_request
        credential_offer.save()

        return credential_request

    @pytest.fixture
    def second_cred_request(self, second_credential_request, second_credential_offer):
        second_credential_offer.credential_request = second_credential_request
        second_credential_offer.save()

        return second_credential_request

    def test_revoke_credential_request(self, set_up, cred_request):
        assert cred_request.revoked_credential is False
        data = {
            "action": "revoke_credential_request",
            "_selected_action": [
                cred_request.id,
            ],
        }

        self.client.login(username=self.username, password=self.password)
        result = self.client.post(self.change_url, data, follow=True)
        self.client.logout()

        assert result.status_code == status.HTTP_200_OK
        self.revoke_mocker.assert_called_once_with(
            {
                "cred_ex_id": "40b771aa-3d77-4171-b8d5-e1da4fcc4620",
                "publish": True,
            }
        )

        cred_request.refresh_from_db()
        assert cred_request.revoked_credential is True

    def test_revoke_several_credential_requests(self, set_up, cred_request, second_cred_request):
        assert cred_request.revoked_credential is False
        assert second_cred_request.revoked_credential is False

        data = {
            "action": "revoke_credential_request",
            "_selected_action": [
                cred_request.id,
                second_cred_request.id,
            ],
        }

        self.client.login(username=self.username, password=self.password)
        result = self.client.post(self.change_url, data, follow=True)
        self.client.logout()

        assert result.status_code == status.HTTP_200_OK
        self.revoke_mocker.assert_has_calls(
            [
                call(
                    {
                        "cred_ex_id": "40b771aa-3d77-4171-b8d5-e1da4fcc4620",
                        "publish": True,
                    }
                ),
                call(
                    {
                        "cred_ex_id": "b4cb054e-5a08-455e-b7a9-fef47d0957e5",
                        "publish": True,
                    }
                ),
            ],
            any_order=True,
        )

        cred_request.refresh_from_db()
        assert cred_request.revoked_credential is True

        second_cred_request.refresh_from_db()
        assert second_cred_request.revoked_credential is True

    def test_does_not_revoke_credential_request_when_acapy_raises_exception(
        self, set_up, mocker, cred_request
    ):
        assert cred_request.revoked_credential is False
        mock_revoke_credential = mocker.patch.object(
            ACAPy, "send_revoke_credential", return_value={}, side_effect=Exception()
        )

        data = {
            "action": "revoke_credential_request",
            "_selected_action": [
                cred_request.id,
            ],
        }

        self.client.login(username=self.username, password=self.password)
        result = self.client.post(self.change_url, data, follow=True)
        self.client.logout()

        assert result.status_code == status.HTTP_200_OK
        mock_revoke_credential.assert_called_once_with(
            {
                "cred_ex_id": "40b771aa-3d77-4171-b8d5-e1da4fcc4620",
                "publish": True,
            }
        )

        cred_request.refresh_from_db()
        assert cred_request.revoked_credential is False

    def test_does_not_revoke_several_credential_requests_when_cred_offer_not_exist(
        self, set_up, cred_request, second_credential_request
    ):
        assert cred_request.revoked_credential is False
        assert second_credential_request.revoked_credential is False

        data = {
            "action": "revoke_credential_request",
            "_selected_action": [
                cred_request.id,
                second_credential_request.id,
            ],
        }

        self.client.login(username=self.username, password=self.password)
        result = self.client.post(self.change_url, data, follow=True)
        self.client.logout()

        assert result.status_code == status.HTTP_200_OK
        self.revoke_mocker.assert_called_once_with(
            {
                "cred_ex_id": "40b771aa-3d77-4171-b8d5-e1da4fcc4620",
                "publish": True,
            }
        )

        cred_request.refresh_from_db()
        assert cred_request.revoked_credential is True

        second_credential_request.refresh_from_db()
        assert second_credential_request.revoked_credential is False
