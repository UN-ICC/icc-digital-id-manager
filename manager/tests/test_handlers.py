import pytest

from aca.client import ACAClient
from manager.handlers import ACAPy


class TestAcaPy:
    class TestCreateCredentialDefinition:
        credential_json = {"something": "blah"}
        mock_create_cred_def_result_ok = {
            "credential_definition_id": "test-credential-definition-id",
            "any_other_field": "1234",
        }
        mock_create_cred_def_result_bad = {
            "credential_definition": "test-credential-definition-id",
            "any_other_field_ignore_this": 2,
        }

        def test_ok(self, mocker):
            mocker.patch.object(
                ACAClient,
                "create_credential_definition",
                return_value=self.mock_create_cred_def_result_ok,
            )
            result = ACAPy().create_credential_definition(self.credential_json)

            assert result == self.mock_create_cred_def_result_ok

        def test_error(self, mocker):
            mocker.patch.object(
                ACAClient,
                "create_credential_definition",
                return_value=self.mock_create_cred_def_result_ok,
                side_effect=Exception(),
            )
            with pytest.raises(Exception):
                ACAPy().create_credential_definition(self.credential_json)

        def test_no_cred_def_id(self, mocker):
            mocker.patch.object(
                ACAClient,
                "create_credential_definition",
                return_value=self.mock_create_cred_def_result_bad,
            )

            result = ACAPy().create_credential_definition(self.credential_json)
            assert result == self.mock_create_cred_def_result_bad

    class TestCreateSchema:
        mock_create_schema_result = {"schema_id": "test-schema-id", "any_other_field": "1234"}

        def test_ok(self, mocker):
            mocker.patch.object(
                ACAClient,
                "create_schema",
                return_value=self.mock_create_schema_result,
            )
            result = ACAPy().create_schema({"something": "blah"})

            assert result == self.mock_create_schema_result

        def test_error(self, mocker):
            mocker.patch.object(
                ACAClient,
                "create_schema",
                return_value=self.mock_create_schema_result,
                side_effect=Exception(),
            )
            with pytest.raises(Exception):
                ACAPy().create_schema({"something": "blah"})

    class TestRevokeCredential:
        def test_ok(self, mocker):
            mocker.patch.object(
                ACAClient,
                "send_revocation_revoke",
                return_value={},
            )
            result = ACAPy().send_revoke_credential({"something": "blah"})

            assert result == {}

        def test_error(self, mocker):
            mocker.patch.object(
                ACAClient, "send_revocation_revoke", return_value={}, side_effect=Exception()
            )
            with pytest.raises(Exception):
                ACAPy().send_revoke_credential({"something": "blah"})

    class TestOutOfBandReceiveInvitation:
        def test_ok(self, mocker):
            mocker.patch.object(
                ACAClient,
                "out_of_band_receive_invitation",
                return_value={},
            )
            result = ACAPy().out_of_band_receive_invitation({"something": "blah"})

            assert result == {}

        def test_error(self, mocker):
            mocker.patch.object(
                ACAClient,
                "out_of_band_receive_invitation",
                return_value={},
                side_effect=Exception(),
            )
            with pytest.raises(Exception):
                ACAPy().out_of_band_receive_invitation({"something": "blah"})

    class TestReceiveInvitation:
        def test_ok(self, mocker):
            mocker.patch.object(
                ACAClient,
                "accept_connection_invitation",
                return_value={},
            )
            result = ACAPy().accept_connection_invitation({"something": "blah"})

            assert result == {}

        def test_error(self, mocker):
            mocker.patch.object(
                ACAClient,
                "accept_connection_invitation",
                return_value={},
                side_effect=Exception(),
            )
            with pytest.raises(Exception):
                ACAPy().accept_connection_invitation({"something": "blah"})