from datetime import datetime
from unittest.mock import call, patch

import pytest
from django.utils import timezone
from freezegun import freeze_time
from post_office import mail
from requests import HTTPError
from rest_framework import status

from aca.client import ACAClient
from manager.handlers import ACAPy
from manager.models import (
    ConnectionInvitation,
    CredentialDefinition,
    CredentialRequest,
    Organization,
    Schema,
)
from manager.tests.api_view_test_classes import (
    TestListAPIView,
    TestListCreateAPIView,
    TestListCreateDestroyAPIView,
    TestRetrieveAPIView,
    TestRetrieveDestroyAPIView,
)
from manager.tests.factories import OrganizationFactory, SchemaFactory
from manager.utils import QRCodeHandler


@pytest.mark.django_db
class TestSchemaViewSet(TestListCreateAPIView, TestRetrieveAPIView):
    __test__ = True
    path = "schema/"

    mock_datetime = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    @pytest.fixture
    def setup(self, some_organization, mocker):
        self.post_data = {
            "name": "some_name",
            "organization_name": some_organization.pk,
            "schema_json": {
                "schema_name": "some_schema_name",
                "schema_version": "some_schema_version",
                "attributes": ["foo", "bar"],
            },
        }

        mock_create_schema_result = {"schema_id": "some_schema_id"}
        mocker.patch.object(
            ACAClient,
            "create_schema",
            return_value=mock_create_schema_result,
        )
        return some_organization

    def test_create_schema_with_valid_data_ok(
        self, mocker, admin_user, authenticate, some_organization
    ):
        mock_create_schema_result = {"schema_id": "some_schema_id"}
        mock_upload_schema = mocker.patch.object(
            ACAClient,
            "create_schema",
            return_value=mock_create_schema_result,
        )
        body = {
            "name": "some_name",
            "organization_name": some_organization.pk,
            "schema_json": {
                "schema_name": "some_schema_name",
                "schema_version": "some_schema_version",
                "attributes": ["foo", "bar"],
            },
        }

        response = self.client.post(f"/{self.path}", body, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["name"] == body["name"]
        assert response.json()["schema_id"] == mock_create_schema_result["schema_id"]
        assert response.json()["creator"]["username"] == admin_user.username
        assert response.json()["organization"] == some_organization.pk
        created_schema = Schema.objects.get(name=body["name"])
        assert body["name"] == created_schema.name
        assert mock_create_schema_result["schema_id"] == created_schema.schema_id
        assert admin_user.id == created_schema.creator_id
        assert body["organization_name"] == created_schema.organization_id
        assert body["schema_json"] == created_schema.schema_json
        mock_upload_schema.assert_called_once_with(body["schema_json"])

    def test_create_schema_without_mandatory_fields_returns_400(self, authenticate):
        wrong_body = {
            "name": "some_name",
            "schema_json": {
                "schema_name": "some_schema_name",
                "schema_version": "some_schema_version",
                "attributes": ["foo", "bar"],
            },
        }

        response = self.client.post(f"/{self.path}", wrong_body, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"organization_name": ["This field is required."]}

    def test_list_schemas_ok(self, authenticate):
        SchemaFactory.create_batch(5)

        response = self.client.get(f"/{self.path}")

        expected_schema_fields = [
            "id",
            "schema_json",
            "creator",
            "created",
            "modified",
            "name",
            "schema_id",
            "enabled",
            "organization",
        ]
        results = response.json()["results"]
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == Schema.objects.count()
        assert all(field in results[0].keys() for field in expected_schema_fields)

    def test_list_schemas_search_by_organization_ok(self, authenticate):
        some_organization = OrganizationFactory()
        SchemaFactory.create_batch(5, organization=some_organization)
        other_organization = OrganizationFactory()
        SchemaFactory.create_batch(3, organization=other_organization)

        search = {"search": some_organization.name}
        response = self.client.get(f"/{self.path}", data=search)

        results = response.json()["results"]
        expected_schemas = Schema.objects.filter(
            organization__name__icontains=some_organization.name
        )
        expected_schemas_ids = expected_schemas.values_list("id", flat=True)
        non_expected_schemas_ids = Schema.objects.exclude(
            organization__name__icontains=some_organization.name
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == expected_schemas.count()
        assert all(schema["id"] in expected_schemas_ids for schema in results)
        assert all(schema["id"] not in non_expected_schemas_ids for schema in results)

    def test_list_schemas_ordering_by_name_ok(self, authenticate):
        SchemaFactory.create_batch(5)

        ordering = {"ordering": "name"}
        response = self.client.get(f"/{self.path}", data=ordering)

        expected_ordered_schemas = Schema.objects.order_by("name")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["results"][0]["id"] == expected_ordered_schemas[0].id
        assert response.json()["results"][1]["id"] == expected_ordered_schemas[1].id
        assert response.json()["results"][2]["id"] == expected_ordered_schemas[2].id
        assert response.json()["results"][3]["id"] == expected_ordered_schemas[3].id
        assert response.json()["results"][4]["id"] == expected_ordered_schemas[4].id

    def test_list_schemas_filter_by_enabled_ok(self, authenticate):
        SchemaFactory.create_batch(2, enabled=True)
        SchemaFactory.create_batch(5, enabled=False)

        filtering = {"enabled": False}
        response = self.client.get(f"/{self.path}", data=filtering)

        results = response.json()["results"]
        expected_schemas = Schema.objects.filter(enabled=filtering["enabled"])
        expected_schemas_ids = expected_schemas.values_list("id", flat=True)
        non_expected_schemas_ids = Schema.objects.exclude(enabled=filtering["enabled"]).values_list(
            "id", flat=True
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == expected_schemas.count()
        assert all(schema["id"] in expected_schemas_ids for schema in results)
        assert all(schema["id"] not in non_expected_schemas_ids for schema in results)

    def test_retrieve_non_existent_schema_returns_error(self, authenticate):
        non_existent_schema = getattr(Schema.objects.last(), "id", 0) + 1

        response = self.client.get(f"/{self.path}{non_existent_schema}/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @freeze_time(mock_datetime)
    def test_retrieve_schema_returns_its_fields_ok(self, authenticate):
        schema = SchemaFactory()

        response = self.client.get(f"/{self.path}{schema.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == schema.id
        assert response.json()["name"] == schema.name
        assert response.json()["schema_id"] == schema.schema_id
        assert response.json()["enabled"] == schema.enabled
        assert response.json()["creator"]["username"] == schema.creator.username
        assert response.json()["organization"] == schema.organization.name
        assert response.json()["schema_json"] == schema.schema_json
        assert response.json()["created"] == schema.created.strftime("%Y-%m-%dT%H:%M:%SZ")
        assert response.json()["modified"] == schema.modified.strftime("%Y-%m-%dT%H:%M:%SZ")

    def test_delete_non_existent_schema_returns_error(self, authenticate):
        non_existent_schema = getattr(Schema.objects.last(), "id", 0) + 1

        response = self.client.delete(f"/{self.path}{non_existent_schema}/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_schema_perform_soft_delete_ok(self, authenticate):
        schema = SchemaFactory()

        response = self.client.delete(f"/{self.path}{schema.id}/")

        schema.refresh_from_db()
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not schema.enabled

    def test_update_non_existent_schema_returns_error(self, authenticate):
        non_existent_schema = getattr(Schema.objects.last(), "id", 0) + 1

        response = self.client.put(f"/{self.path}{non_existent_schema}/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @freeze_time(mock_datetime)
    def test_update_schema_creates_new_schema_invalidating_the_updated(
        self, mocker, authenticate, admin_user
    ):
        mock_create_schema_result = {"schema_id": "some_schema_id"}
        mock_upload_schema = mocker.patch.object(
            ACAClient,
            "create_schema",
            return_value=mock_create_schema_result,
        )
        schema_to_update = SchemaFactory()
        organization = OrganizationFactory()

        body = {
            "name": "other_name",
            "organization_name": organization.pk,
            "schema_json": {
                "schema_name": "other_schema_name",
                "schema_version": "some_schema_version",
                "attributes": ["foo", "bar"],
            },
        }
        number_of_schemas = Schema.objects.count()

        response = self.client.put(f"/{self.path}{schema_to_update.id}/", body, format="json")

        schema_to_update.refresh_from_db()
        new_schema = Schema.objects.get(name=body["name"])
        assert response.status_code == status.HTTP_200_OK
        assert Schema.objects.count() == number_of_schemas + 1
        assert not schema_to_update.enabled
        assert body["name"] == new_schema.name
        assert new_schema.schema_id == mock_create_schema_result["schema_id"]
        assert body["organization_name"] == new_schema.organization.name
        assert new_schema.enabled
        assert body["schema_json"] == new_schema.schema_json
        assert new_schema.creator_id == admin_user.id
        assert new_schema.created == self.mock_datetime
        assert new_schema.modified == self.mock_datetime
        mock_upload_schema.assert_called_once_with(body["schema_json"])

    def test_update_schema_with_non_valid_data_returns_error(self, authenticate):
        schema_to_update = SchemaFactory()
        non_existent_organization = getattr(Organization.objects.last(), "id", 0) + 1
        wrong_body = {
            "name": "other_name",
            "organization_name": non_existent_organization,
            "schema_json": {
                "schema_name": "other_schema_name",
                "schema_version": "some_schema_version",
                "attributes": ["foo", "bar"],
            },
        }

        response = self.client.put(f"/{self.path}{schema_to_update.id}/", wrong_body, format="json")

        schema_to_update.refresh_from_db()
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"organization_name": ["Organization does not exist"]}
        assert schema_to_update.enabled


@pytest.mark.django_db
class TestCredentialRequestRetrieveDestroyAPIView(TestRetrieveDestroyAPIView):
    __test__ = True
    path_base = "credential-request"
    test_pk = "1"
    path = f"{path_base}/{test_pk}"

    @pytest.fixture
    def delete_response(self, credential_request):
        return self.client.delete(f"/{self.path}")

    @pytest.fixture
    def mock_revoke_credential(self, mocker):
        return mocker.patch.object(ACAPy, "send_revoke_credential", return_value={})

    @pytest.fixture
    def setup(self, credential_request, credential_offer, mock_revoke_credential):
        credential_offer.credential_request = credential_request
        credential_offer.save()

        self.mock_revoke_credential = mock_revoke_credential
        return credential_request

    @pytest.mark.usefixtures("connection_invitation", "credential_offer")
    def test_retrieve(self, authenticate, credential_request):
        response = self.client.get(f"/{self.path_base}/{credential_request.id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.data

        assert data == {
            "id": 1,
            "code": "12345",
            "cred_def_id": "testcredentialdefinition:1:2:3:test",
            "invitation_url": "http://test.com/deep-link-redirect/12345",
            "connection_accepted": False,
            "credential_offer_accepted": False,
            "revoked_credential": False,
            "connection_invitation_url": "Imludml0YXRpb24udGVzdC51cmwi",
        }

        assert data["code"] == "12345"
        assert response.get("ETag")

    def test_destroy_soft(self, authenticate, setup):
        cred_request = setup
        assert cred_request.revoked_credential is False

        response = self.client.delete(f"/{self.path_base}/{cred_request.id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT

        self.mock_revoke_credential.assert_called_once_with(
            {
                "cred_ex_id": "40b771aa-3d77-4171-b8d5-e1da4fcc4620",
                "publish": True,
            }
        )

        cred_request.refresh_from_db()
        assert cred_request.revoked_credential is True

    def test_destroy_raises_exception_when_acapy_raise_exception(self, authenticate, setup, mocker):
        cred_request = setup
        mock_revoke_credential = mocker.patch.object(
            ACAPy, "send_revoke_credential", return_value={}, side_effect=Exception()
        )

        assert cred_request.revoked_credential is False

        response = self.client.delete(f"/{self.path_base}/{cred_request.id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        mock_revoke_credential.assert_called_once_with(
            {
                "cred_ex_id": "40b771aa-3d77-4171-b8d5-e1da4fcc4620",
                "publish": True,
            }
        )

        cred_request.refresh_from_db()
        assert cred_request.revoked_credential is False

    def test_destroy_soft_raises_exception_when_credential_offer_not_exist(
        self, authenticate, credential_request, mocker
    ):

        assert credential_request.revoked_credential is False
        mock_revoke_credential = mocker.patch.object(
            ACAPy, "send_revoke_credential", return_value={}
        )

        response = self.client.delete(f"/{self.path_base}/{credential_request.id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        mock_revoke_credential.assert_not_called()

        credential_request.refresh_from_db()
        assert credential_request.revoked_credential is False


@pytest.mark.django_db
class TestCredentialRequestListCreateAPIView(TestListCreateAPIView):
    __test__ = True
    path = "credential-request"
    post_data = {
        "credential_definition": "testcredentialdefinition:1:2:3:test",
        "email": "test@mail.com",
        "credential_data": '{ "schema_key_1": "Silly String 1", "schema_key_2": "Silly String 2" }',
    }
    post_data_2 = {
        "credential_definition": "secondtestcredentialdefinition:1:2:3:secondtest",
        "email": "secondtest@mail.com",
        "credential_data": '{ "second_schema_key_1": "Serious String 1", '
        '"second_schema_key_2": "Serious String 2" }',
    }
    uuid_length = 36

    @pytest.fixture
    def setup(self, credential_request, mocker):
        mocker.patch(
            "manager.handlers.connection_invitation_create",
            return_value=("invitation.url", "e30="),
        )
        mocker.patch.object(
            QRCodeHandler,
            "text_to_qr",
            return_value="invitation.url",
        )
        return credential_request

    def test_list(self, authenticate, setup):
        assert CredentialRequest.objects.all().first()
        response = self.client.get(f"/{self.path}")
        assert response.status_code == status.HTTP_200_OK
        assert response.get("ETag")
        assert len(response.data.get("results")) == 1
        assert response.data["results"][0] == {
            "cred_def_id": "testcredentialdefinition:1:2:3:test",
            "code": "12345",
            "invitation_url": "http://test.com/deep-link-redirect/12345",
            "id": 1,
            "revoked_credential": False,
            "connection_accepted": False,
            "credential_offer_accepted": False,
            "connection_invitation_url": "bnVsbA==",
        }

    @patch.object(mail, "send")
    def test_create(
        self, mock_send, authenticate, setup, credential_definition, invitation_template
    ):
        previous_elements_count = CredentialRequest.objects.count()

        response = self.client.post(f"/{self.path}", self.post_data)

        assert response.status_code == status.HTTP_201_CREATED
        assert not isinstance(response.data, list)
        assert response.status_code == status.HTTP_201_CREATED
        elements = CredentialRequest.objects.all()
        assert elements.count() == previous_elements_count + 1
        request = elements.first()
        code = request.code
        assert len(code) == self.uuid_length
        assert code == response.data["code"]
        invitation_url = request.invitation_url
        assert invitation_url == response.data["invitation_url"]
        assert invitation_url == f"http://test.com/deep-link-redirect/{code}"
        id_response = request.id
        assert id_response == response.data["id"]
        cred_def_id = request.cred_def_id
        assert cred_def_id == "testcredentialdefinition:1:2:3:test"

        mock_send.assert_called()

    def create_multi(self, data, mock_send):
        response = self.client.post(f"/{self.path}", data, format="json")

        assert isinstance(response.data, list)
        response_length = len(response.data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response_length == 2
        elements = CredentialRequest.objects.all()
        assert elements.count() == 3

        for i in range(response_length):
            response_entry = response.data[i]
            code_in_response = response_entry["code"]
            credential_request = elements.filter(code=code_in_response).first()
            code = credential_request.code
            assert len(code) == self.uuid_length
            assert (
                credential_request.credential_definition.credential_id
                == data[i]["credential_definition"]
            )
            invitation_url = credential_request.invitation_url
            assert invitation_url == response_entry["invitation_url"]
            assert invitation_url == f"http://test.com/deep-link-redirect/{code}"
            id_response = credential_request.id
            assert id_response == response_entry["id"]
            mock_send.assert_called()

    @patch.object(mail, "send")
    def test_create_multi(
        self,
        mock_send,
        authenticate,
        setup,
        credential_definition,
        second_credential_definition,
        invitation_template,
    ):
        data = [self.post_data, self.post_data_2]
        self.create_multi(data, mock_send)

    @patch.object(mail, "send")
    def test_create_multi_duplicate(
        self, mock_send, authenticate, setup, credential_definition, invitation_template
    ):
        data = [self.post_data, self.post_data]
        self.create_multi(data, mock_send)

    @patch.object(mail, "send")
    def test_create_multi_with_forwarding_connection_error(
        self, authenticate, setup, credential_definition, invitation_template
    ):
        data = [self.post_data]
        response = self.client.post(f"/{self.path}", data, format="json")
        assert response.status_code == 401

    @patch.object(mail, "send")
    def test_create_two_same_data(self, mock_send, authenticate, setup, credential_definition):
        test_credential = CredentialRequest.objects.filter(email="test@mail.com")
        assert not test_credential.exists()

        response1 = self.client.post(f"/{self.path}", self.post_data)
        assert response1.status_code == status.HTTP_201_CREATED
        code1 = response1.data["code"]
        assert len(code1) == self.uuid_length

        response2 = self.client.post(f"/{self.path}", self.post_data)
        assert response2.status_code == status.HTTP_201_CREATED
        code2 = response2.data["code"]
        assert len(code2) == self.uuid_length
        assert code1 != code2

        assert test_credential.count() == 2
        assert CredentialRequest.objects.filter(code=code1).exists()
        assert CredentialRequest.objects.filter(code=code2).exists()


@pytest.mark.django_db
class TestCredentialDefinitionAPIView(TestListCreateDestroyAPIView):
    __test__ = True
    path = "credential-definition/"

    @pytest.fixture
    def delete_response(self, credential_definition):
        return self.client.delete(f"/{self.path}{credential_definition.id}/")

    @pytest.fixture
    def mock_create_aca_py_cred_def(self, mocker):
        return mocker.patch.object(
            ACAClient,
            "create_credential_definition",
            return_value={
                "credential_definition_id": "anothertestcredentialdefinition:1:2:3:test",
                "any_other_field": "1234",
            },
        )

    @pytest.fixture
    def setup(self, schema, credential_definition, mock_create_aca_py_cred_def):
        self.post_data = {
            "name": "another_test_credential_definition",
            "credential_id": "anothertestcredentialdefinition:1:2:3:test",
            "schema": schema.schema_id,
            "support_revocation": "True",
            "revocation_registry_size": 100,
        }
        self.mock_create_aca_py_cred_def = mock_create_aca_py_cred_def
        return credential_definition

    def test_retrieve(self, authenticate, setup, get_response):
        response = self.client.get(
            path=f"/{self.path}",
        )
        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) == 1
        cred_def = results[0]
        assert cred_def["credential_id"] == "testcredentialdefinition:1:2:3:test"
        assert cred_def["name"] == "credential_definition"
        assert cred_def["enabled"] is True
        assert cred_def["schema"] == "testschema:1:id:1.0"
        assert cred_def["support_revocation"] is True
        assert cred_def["creator"] == 1

    def test_create_wrong_params(self, authenticate, setup, schema):
        post_data = {
            "name": "wrong_test_credential_definition",
            "credential_id": "wrongtestcredentialdefinition:1:2:3:test",
            "schema_id": schema.schema_id,
            "support_revocation": "False",
        }
        assert not CredentialDefinition.objects.filter(
            credential_id="wrongtestcredentialdefinition:1:2:3:test"
        ).first()
        response = self.client.post(
            path=f"/{self.path}",
            data=post_data,
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "This field is required" in str(response.data)
        assert "schema" in str(response.data)

    def test_create_already_exists(self, authenticate, setup, credential_definition):
        post_data = {
            "name": "another_test_credential_definition",
            "credential_id": credential_definition.credential_id,
            "schema": credential_definition.schema.schema_id,
            "support_revocation": "False",
        }
        assert CredentialDefinition.objects.filter(
            credential_id=credential_definition.credential_id
        ).first()
        response = self.client.post(
            path=f"/{self.path}",
            data=post_data,
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert str(response.data) == (
            "{'credential_id': [ErrorDetail(string='credential definition with this "
            "credential id already exists.', code='unique')]}"
        )
        assert not CredentialDefinition.objects.filter(
            name="another_test_credential_definition"
        ).first()

        self.mock_create_aca_py_cred_def.assert_not_called()

    def test_create(self, authenticate, setup):
        assert not CredentialDefinition.objects.filter(
            name="another_test_credential_definition"
        ).first()
        response = self.client.post(
            path=f"/{self.path}",
            data=self.post_data,
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        cred_def = response.data
        assert cred_def["name"] == "another_test_credential_definition"
        assert cred_def["credential_id"] == "anothertestcredentialdefinition:1:2:3:test"
        assert cred_def["support_revocation"] is True
        assert cred_def["revocation_registry_size"] == 100

        assert CredentialDefinition.objects.filter(
            name="another_test_credential_definition"
        ).first()
        get_from_db_by_id = CredentialDefinition.objects.filter(
            credential_id="anothertestcredentialdefinition:1:2:3:test"
        ).all()
        assert get_from_db_by_id
        assert len(get_from_db_by_id) == 1
        assert get_from_db_by_id.first().credential_json() == {
            "schema_id": "testschema:1:id:1.0",
            "tag": "another_test_credential_definition",
            "support_revocation": True,
            "revocation_registry_size": 100,
        }
        self.mock_create_aca_py_cred_def.assert_called_once_with(
            {
                "schema_id": "testschema:1:id:1.0",
                "tag": "another_test_credential_definition",
                "support_revocation": True,
                "revocation_registry_size": 100,
            }
        )

    def test_create_when_schema_does_not_exist(self, authenticate, setup):
        post_data = {
            "name": "yet_another_test_credential_definition",
            "credential_id": "testcredentialdefinitionschemadoesnotexist:1:2:3:test",
            "schema": "nonexistentschema:1:2:3:test",
            "support_revocation": "False",
        }
        response = self.client.post(
            path=f"/{self.path}",
            data=post_data,
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert (
            str(response.data) == "{'schema': [ErrorDetail(string='A schema with schema_id "
            "\"nonexistentschema:1:2:3:test\" does not exist', code='does_not_exist')]}"
        )
        assert not CredentialDefinition.objects.filter(
            name="yet_another_test_credential_definition"
        ).first()
        self.mock_create_aca_py_cred_def.assert_not_called()

    def test_post_with_authentication_bad_request(self, authenticate, post_response, setup):
        response = self.client.post(
            path=f"/{self.path}",
            data={},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        self.mock_create_aca_py_cred_def.assert_not_called()

    def test_delete_is_soft(self, authenticate, setup, credential_definition):
        cred_def = CredentialDefinition.objects.filter(id=credential_definition.id).first()
        assert cred_def
        assert cred_def.enabled

        response = self.client.delete(
            path=f"/{self.path}{credential_definition.id}/",
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        self.mock_create_aca_py_cred_def.assert_not_called()
        after_cred_def = CredentialDefinition.objects.filter(id=credential_definition.id).first()
        assert after_cred_def
        assert not after_cred_def.enabled


@pytest.mark.django_db
class TestCredentialOfferListAPIView(TestListAPIView):
    __test__ = True
    path = "credential-offer"

    @pytest.fixture
    def setup(self, credential_offer, second_credential_offer, mocker):
        self.mock = mocker.patch.object(
            ACAClient,
            "retrieve_issue_credential_by_cred_ex_id",
            return_value={
                "revocation_id": "12",
                "credential_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            },
        )

        return credential_offer

    def test_retrieve_list(self, authenticate, setup):
        response = self.client.get(f"/{self.path}")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "count": 2,
            "next": None,
            "previous": None,
            "results": [
                {
                    "id": 1,
                    "accepted": False,
                    "connection_id": "1",
                    "cred_ex_id": "40b771aa-3d77-4171-b8d5-e1da4fcc4620",
                    "credential_request": 1,
                    "revocation_id": None,
                    "credential_id": None,
                    "offer_json": '{"offer_key_1": "offer_value_1", '
                    '"offer_key_2": "offer_value_2"}',
                    "created": "2020-01-01T00:00:00Z",
                    "modified": "2020-01-01T00:00:00Z",
                },
                {
                    "id": 2,
                    "accepted": False,
                    "connection_id": "2",
                    "cred_ex_id": "b4cb054e-5a08-455e-b7a9-fef47d0957e5",
                    "credential_request": 2,
                    "revocation_id": None,
                    "credential_id": None,
                    "offer_json": '{"offer_key_1": "offer_value_1", '
                    '"offer_key_2": "offer_value_2"}',
                    "created": "2020-01-01T00:00:00Z",
                    "modified": "2020-01-01T00:00:00Z",
                },
            ],
        }

        self.mock.assert_not_called()

    @freeze_time(datetime(2022, 2, 2, tzinfo=timezone.utc))
    def test_retrieve_list_filter_by_cred_req_id(
        self, authenticate, setup, second_credential_offer, second_credential_request
    ):
        second_credential_offer.revocation_id = None
        second_credential_offer.save()

        response = self.client.get(f"/{self.path}?credential_request=2")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "count": 1,
            "next": None,
            "previous": None,
            "results": [
                {
                    "id": 2,
                    "accepted": False,
                    "connection_id": "2",
                    "cred_ex_id": "b4cb054e-5a08-455e-b7a9-fef47d0957e5",
                    "credential_request": 2,
                    "revocation_id": "12",
                    "credential_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "offer_json": '{"offer_key_1": "offer_value_1", '
                    '"offer_key_2": "offer_value_2"}',
                    "created": "2020-01-01T00:00:00Z",
                    "modified": "2022-02-02T00:00:00Z",
                }
            ],
        }

        self.mock.assert_has_calls([call(second_credential_offer.cred_ex_id)])


@pytest.mark.django_db
class TestConnectionInvitationView:
    url = "/connection-invitation"
    body = {
        "invitation_json": {
            "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/connections/1.0/invitation",
            "@id": "411b15f5-a557-415c-9daa-ee73d6a50fca",
            "handshake_protocols": ["did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/didexchange/1.0"],
            "services": [
                {
                    "id": "#inline",
                    "type": "did-communication",
                    "recipientKeys": ["did:key:z6Mkgr22AtQPR82HrZ6wfz4N4JYrskcRXpsjVE4VqQkHhyyy"],
                    "serviceEndpoint": "http://192.168.1.140:9905",
                }
            ],
            "label": "Invitation to Barry",
        }
    }

    def test_return_401_when_unauthorized_client(self, api_client):
        response = api_client.post(self.url, data=self.body, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_accept_connection_invitation(self, api_client_admin, mocker):
        accept_invitation_mock = mocker.patch.object(
            ACAClient,
            "accept_connection_invitation",
            return_value={
                "state": "done",
                "oob_id": "64046333-62d7-43a8-8bdd-c39c350143d5",
                "trace": False,
                "invitation": {
                    "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/connections/1.0/invitation",
                    "@id": "50770fc1-496a-4616-aa27-fb1a93f5a70d",
                    "services": [
                        {
                            "id": "#inline",
                            "type": "did-communication",
                            "recipientKeys": [
                                "did:key:z6MkwUuaCoJcmtuoe92BvHk39wSMKCHySs6eWh5y1qmDmP7L"
                            ],
                            "serviceEndpoint": "http://192.168.1.140:9905",
                        }
                    ],
                    "label": "Invitation to Barry",
                    "handshake_protocols": ["did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/didexchange/1.0"],
                },
                "created_at": "2023-05-15T10:49:44.486639Z",
                "role": "receiver",
                "invi_msg_id": "50770fc1-496a-4616-aa27-fb1a93f5a70d",
                "connection_id": "f8f77223-a9c1-4603-83d3-09473b2a6de3",
                "updated_at": "2023-05-15T10:49:44.486639Z",
            },
        )

        response = api_client_admin.post(self.url, data=self.body, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert "connection_id" in response.json()
        accept_invitation_mock.assert_called_once_with(self.body["invitation_json"])

        conn_inv = ConnectionInvitation.objects.all()
        assert conn_inv.count() == 1

        connection_invitation = conn_inv[0]
        assert connection_invitation.connection_id == "f8f77223-a9c1-4603-83d3-09473b2a6de3"
        assert connection_invitation.invitation_json == self.body["invitation_json"]
        assert connection_invitation.accepted is True

    def test_does_not_create_connection_invitation_when_accept_connection_invitation_raise_error(
        self, api_client_admin, mocker
    ):
        receive_invitation_mock = mocker.patch.object(
            ACAClient, "accept_connection_invitation", side_effect=Exception("cannot connect")
        )

        response = api_client_admin.post(self.url, data=self.body, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == "Error establishing connection, error: cannot connect"
        receive_invitation_mock.assert_called_once()


@pytest.mark.django_db
class TestCredentialView:
    url = "/credential"

    @pytest.fixture
    def conn_invitation(self, conn_invitation_without_cred_request):
        conn_invitation_without_cred_request.accepted = True
        conn_invitation_without_cred_request.save()

        return conn_invitation_without_cred_request

    @pytest.fixture(autouse=True)
    def setup(self, mocker, conn_invitation, credential_definition, schema):
        self.body = {
            "connection_id": conn_invitation.connection_id,
            "cred_def_id": credential_definition.credential_id,
            "credential_data": {"schema_key_1": "1", "schema_key_2": "2"},
        }
        self.mock_cred_offer = mocker.patch(
            "manager.views.credential_offer_create",
            return_value={
                "connection_id": "144e7275-c43b-40a9-a8d9-e42078f56427",
                "cred_def_id": "AQupvo8VaZdQFc7Gn6Rs3d:3:CL:22:test_malawi",
            },
        )

    def test_return_401_when_unauthorized_client(self, api_client):
        response = api_client.post(self.url, data=self.body, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_201_create_credential_request(
        self,
        api_client_admin,
        admin_user,
        conn_invitation_without_cred_request,
        credential_definition,
    ):
        response = api_client_admin.post(self.url, data=self.body, format="json")

        assert response.status_code == status.HTTP_201_CREATED

        cred_request = CredentialRequest.objects.all()
        assert cred_request.count() == 1

        credential_request = cred_request[0]

        assert response.json() == {
            "connection_id": "144e7275-c43b-40a9-a8d9-e42078f56427",
            "cred_def_id": "AQupvo8VaZdQFc7Gn6Rs3d:3:CL:22:test_malawi",
            "cred_request_id": credential_request.id,
        }

        self.mock_cred_offer.assert_called_once_with(
            conn_invitation_without_cred_request.connection_id, conn_invitation_without_cred_request
        )

        cred_request = CredentialRequest.objects.all()
        assert cred_request.count() == 1

        credential_request = cred_request[0]
        assert (
            credential_request.credential_definition.credential_id
            == credential_definition.credential_id
        )
        assert credential_request.credential_data == {"schema_key_1": "1", "schema_key_2": "2"}
        assert credential_request.creator == admin_user

        conn_invitation_without_cred_request.refresh_from_db()
        assert conn_invitation_without_cred_request.credential_request == credential_request

    def test_returns_403_when_connection_not_ready(
        self,
        mocker,
        api_client_admin,
        admin_user,
        conn_invitation_without_cred_request,
        credential_definition,
    ):
        mock_response = mocker.Mock()
        mock_response.text = "403: Connection not ready"

        mocker_offer = mocker.patch(
            "manager.views.credential_offer_create", side_effect=HTTPError(response=mock_response)
        )

        response = api_client_admin.post(self.url, data=self.body, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        mocker_offer.assert_called_once()

    def test_create_con_invitation_when_same_connection_invitation_given(
        self, mocker, api_client_admin, credential_definition, conn_invitation, credential_request
    ):
        conn_invitation.credential_request = credential_request
        conn_invitation.save()

        con_invitation = ConnectionInvitation.objects.all()
        assert con_invitation.count() == 1

        mocker.patch(
            "manager.views.CredentialView._create_credential_request",
            return_value=credential_request,
        )

        response = api_client_admin.post(self.url, data=self.body, format="json")

        assert response.status_code == status.HTTP_201_CREATED

        connections_invitations = ConnectionInvitation.objects.all()
        assert connections_invitations.count() == 2

        for con_invitation in connections_invitations:
            assert con_invitation.credential_request == credential_request

    def test_assign_related_cred_request_when_new_connection_invitation_given(
        self, mocker, api_client_admin, credential_definition, conn_invitation, credential_request
    ):
        assert conn_invitation.credential_request is None
        con_invitation = ConnectionInvitation.objects.all()
        assert con_invitation.count() == 1

        mocker.patch(
            "manager.views.CredentialView._create_credential_request",
            return_value=credential_request,
        )

        response = api_client_admin.post(self.url, data=self.body, format="json")

        assert response.status_code == status.HTTP_201_CREATED

        connections_invitations = ConnectionInvitation.objects.all()
        assert connections_invitations.count() == 1

        conn_invitation.refresh_from_db()
        assert conn_invitation.credential_request == credential_request
