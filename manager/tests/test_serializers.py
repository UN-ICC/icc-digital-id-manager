import json

import pytest
from rest_framework import serializers
from rest_framework.exceptions import ErrorDetail
from rest_framework.serializers import ModelSerializer

from manager.serializers import (
    CredentialDefinitionSerializer,
    CredentialRequestSerializer,
    CredentialSerializer,
    SchemaSerializer,
)


@pytest.mark.django_db
class TestCredentialRequestSerializer:
    def test_validate_credential_definition_not_found(self, mocker):
        run_validation = mocker.patch.object(ModelSerializer, "run_validation")
        validate_credential_data = mocker.patch.object(
            CredentialRequestSerializer, "_validate_credential_data"
        )
        s = CredentialRequestSerializer(
            data={"email": "user@mailcom", "credential_definition": "invalid"}
        )
        with pytest.raises(serializers.ValidationError):
            s.is_valid(raise_exception=True)
            run_validation.assert_not_called()
            validate_credential_data.assert_not_called()

    def test_validate_credential_definition_id_found(self, mocker, credential_definition):
        run_validation = mocker.patch.object(ModelSerializer, "run_validation")
        validate_credential_data = mocker.patch.object(
            CredentialRequestSerializer, "_validate_credential_data"
        )
        s = CredentialRequestSerializer(
            data={
                "email": "user@mailcom",
                "credential_definition": credential_definition.credential_id,
            }
        )
        s.is_valid(raise_exception=True)
        run_validation.assert_called_once()
        validate_credential_data.assert_called_once()

    def test_validate_credential_definition_name_found(self, mocker, credential_definition):
        run_validation = mocker.patch.object(ModelSerializer, "run_validation")
        validate_credential_data = mocker.patch.object(
            CredentialRequestSerializer, "_validate_credential_data"
        )
        s = CredentialRequestSerializer(
            data={
                "email": "user@mailcom",
                "credential_definition": credential_definition.name,
            }
        )
        s.is_valid(raise_exception=True)
        run_validation.assert_called_once()
        validate_credential_data.assert_called_once()

    def test_validate_invalid_email(self, mocker, credential_definition):
        validate_credential_data = mocker.patch.object(
            CredentialRequestSerializer, "_validate_credential_data"
        )
        s = CredentialRequestSerializer(
            data={
                "email": "invalid_email",
                "credential_definition": credential_definition.credential_id,
            }
        )
        with pytest.raises(serializers.ValidationError):
            s.is_valid(raise_exception=True)
            validate_credential_data.assert_not_called()

    def test_validate_valid_email(self, mocker, credential_definition):
        validate_credential_data = mocker.patch.object(
            CredentialRequestSerializer, "_validate_credential_data"
        )
        s = CredentialRequestSerializer(
            data={
                "email": "user@mail.com",
                "credential_definition": credential_definition.credential_id,
            }
        )
        s.is_valid(raise_exception=True)
        validate_credential_data.assert_called_once_with(
            {
                "email": "user@mail.com",
                "credential_definition": credential_definition,
            }
        )

    def test_validate_data_invalid(self, credential_definition, schema):
        s = CredentialRequestSerializer(
            data={
                "email": "user@mail.com",
                "credential_definition": credential_definition.credential_id,
                "credential_data": "invalid_json",
            }
        )
        with pytest.raises(serializers.ValidationError):
            s.is_valid(raise_exception=True)

    def test_validate_data_does_not_match_schema(self, credential_definition, schema):
        s = CredentialRequestSerializer(
            data={
                "email": "user@mail.com",
                "credential_definition": credential_definition.credential_id,
                "credential_data": json.dumps({"schema_key_1": "1"}),
            }
        )
        with pytest.raises(serializers.ValidationError):
            s.is_valid(raise_exception=True)

    def test_validate_data_ok(self, credential_definition, schema):
        s = CredentialRequestSerializer(
            data={
                "email": "user@mail.com",
                "credential_definition": credential_definition.credential_id,
                "credential_data": json.dumps({"schema_key_1": "1", "schema_key_2": "2"}),
            }
        )
        s.is_valid(raise_exception=True)


@pytest.mark.django_db
class TestSchemaSerializer:
    def test_validate_data_ok(self, schema, some_organization):
        s = SchemaSerializer(
            data={
                "name": "schema_serializer_test_name",
                "organization_name": some_organization.pk,
                "schema_id": "1234:1:schema_serializer_test_name:1.0",
                "enabled": True,
                "creator": schema.creator,
                "schema_json": {
                    "schema_name": "schema_serializer_test_name",
                    "schema_version": "1.0",
                    "attributes": ["schema_key_1", "schema_key_2"],
                },
            }
        )
        s.is_valid(raise_exception=True)

        assert s.data == {
            "enabled": True,
            "name": "schema_serializer_test_name",
            "organization": some_organization.pk,
            "schema_id": "1234:1:schema_serializer_test_name:1.0",
            "schema_json": {
                "schema_name": "schema_serializer_test_name",
                "schema_version": "1.0",
                "attributes": ["schema_key_1", "schema_key_2"],
            },
        }

    def test_validate_data_wrong_field_name(self, schema):
        s = SchemaSerializer(
            data={
                "name": "schema_serializer_test_name",
                "schema_id": "1234:1:schema_serializer_test_name:1.0",
                "enabled": True,
                "creator": schema.creator,
                "schema_json": {
                    "name": "schema_serializer_test_name",
                    "schema_version": "1.0",
                    "attributes": ["schema_key_1", "schema_key_2"],
                },
            }
        )
        with pytest.raises(serializers.ValidationError):
            s.is_valid(raise_exception=True)


@pytest.mark.django_db
class TestCredentialDefinitionSerializer:
    def test_validate_data_ok(self, schema):
        name = "another_test_credential_definition"
        support_revocation = "True"
        s = CredentialDefinitionSerializer(
            data={
                "name": name,
                "schema": schema.schema_id,
                "support_revocation": support_revocation,
            }
        )
        s.is_valid(raise_exception=True)

        assert s.validated_data == {
            "name": name,
            "schema": schema,
            "support_revocation": bool(support_revocation),
        }

    def test_validate_data_wrong_field_name(self, schema):
        s = CredentialDefinitionSerializer(
            data={
                "names": "name",
                "schema": schema.schema_id,
                "support_revocation": "True",
            }
        )
        with pytest.raises(serializers.ValidationError):
            s.is_valid(raise_exception=True)


@pytest.mark.django_db
@pytest.mark.usefixtures("schema")
class TestCredentialSerializer:
    @pytest.fixture
    def conn_invitation(self, conn_invitation_without_cred_request):
        conn_invitation_without_cred_request.accepted = True
        conn_invitation_without_cred_request.save()

        return conn_invitation_without_cred_request

    def test_validate_data_ok(self, conn_invitation, credential_definition):
        serializer = CredentialSerializer(
            data={
                "connection_id": conn_invitation.connection_id,
                "cred_def_id": credential_definition.credential_id,
                "credential_data": {"schema_key_1": "1", "schema_key_2": "2"},
            }
        )

        assert serializer.is_valid(raise_exception=True)

    @pytest.mark.usefixtures("conn_invitation")
    def test_invalid_connection_id(self, credential_definition):
        serializer = CredentialSerializer(
            data={
                "connection_id": "1234",
                "cred_def_id": credential_definition.credential_id,
                "credential_data": {"schema_key_1": "1", "schema_key_2": "2"},
            }
        )
        with pytest.raises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

        assert serializer.errors == {
            "connection_id": [
                ErrorDetail(
                    string="Connection id '1234' not found in ConnectionInvitation", code="invalid"
                )
            ]
        }

    def test_invalid_connection_id_when_accepted_is_false(
        self, conn_invitation, credential_definition
    ):
        conn_invitation.accepted = False
        conn_invitation.save()

        serializer = CredentialSerializer(
            data={
                "connection_id": conn_invitation.connection_id,
                "cred_def_id": credential_definition.credential_id,
                "credential_data": {"schema_key_1": "1", "schema_key_2": "2"},
            }
        )
        with pytest.raises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

        assert serializer.errors == {
            "connection_id": [
                ErrorDetail(
                    string=f"Connection id '{conn_invitation.connection_id}' is not accepted",
                    code="invalid",
                )
            ]
        }

    def test_invalid_credential_definition(self, conn_invitation, credential_definition):
        serializer = CredentialSerializer(
            data={
                "connection_id": conn_invitation.connection_id,
                "cred_def_id": "definition",
                "credential_data": {"schema_key_1": "1", "schema_key_2": "2"},
            }
        )

        with pytest.raises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

        assert serializer.errors == {
            "cred_def_id": [
                ErrorDetail(
                    string="Credential definition 'definition' does not exist", code="invalid"
                )
            ]
        }

    def test_invalid_credential_data_when_does_not_match_schema(
        self, conn_invitation, credential_definition
    ):
        serializer = CredentialSerializer(
            data={
                "connection_id": conn_invitation.connection_id,
                "cred_def_id": credential_definition.credential_id,
                "credential_data": {"schema_key_1": "1"},
            }
        )

        with pytest.raises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

        assert serializer.errors == {
            "credential_data": [
                ErrorDetail(
                    string="Attribute(s) not found in the data provided: "
                    "{'schema_key_2'}, "
                    "credential_data given: {'schema_key_1': '1'}, "
                    "cred_def_id: 'testcredentialdefinition:1:2:3:test'",
                    code="invalid",
                )
            ]
        }
