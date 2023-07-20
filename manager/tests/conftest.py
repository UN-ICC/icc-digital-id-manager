from datetime import datetime, timezone

import pytest
from django.contrib.auth.models import User
from freezegun import freeze_time
from post_office.models import EmailTemplate
from requests import Response

from manager.models import (
    CredentialDefinition,
    CredentialOffer,
    CredentialRequest,
    Organization,
    Schema,
)
from manager.tests.factories import ConnectionInvitationFactory


@pytest.fixture
def admin_user():
    return User.objects.create_user("admin", "admin@admin.com", "admin123")


@pytest.fixture
def schema(admin_user):
    return Schema.objects.create(
        name="schema",
        schema_id="testschema:1:id:1.0",
        creator=admin_user,
        schema_json={
            "attributes": ["schema_key_1", "schema_key_2"],
        },
    )


@pytest.fixture
def second_schema(admin_user):
    return Schema.objects.create(
        name="second_schema",
        schema_id="secondtestschema:1:id:1.0",
        creator=admin_user,
        schema_json={
            "attributes": ["second_schema_key_1", "second_schema_key_2"],
        },
    )


@pytest.fixture
def credential_definition(schema, admin_user):
    return CredentialDefinition.objects.create(
        name="credential_definition",
        credential_id="testcredentialdefinition:1:2:3:test",
        schema=schema,
        creator=admin_user,
        support_revocation=True,
    )


@pytest.fixture
def second_credential_definition(second_schema, admin_user):
    return CredentialDefinition.objects.create(
        name="second_credential_definition",
        credential_id="secondtestcredentialdefinition:1:2:3:secondtest",
        schema=second_schema,
        creator=admin_user,
        support_revocation=False,
    )


@pytest.fixture
def credential_request(credential_definition, admin_user):
    return CredentialRequest.objects.create(
        credential_definition=credential_definition,
        creator=admin_user,
        credential_data={
            "credential_data_key_1": "credential_data_value_1",
            "credential_data_key_2": "credential_data_value_2",
        },
        email="test@emails.com",
        code="12345",
    )


@pytest.fixture
def second_credential_request(second_credential_definition, admin_user):
    return CredentialRequest.objects.create(
        credential_definition=second_credential_definition,
        creator=admin_user,
        credential_data={
            "credential_data_key_1": "credential_data_value_1",
            "credential_data_key_2": "credential_data_value_2",
        },
        email="test_2@emails.com",
        code="98765",
    )


@pytest.fixture
@freeze_time(datetime(2020, 1, 1, tzinfo=timezone.utc))
def credential_offer(credential_request):
    return CredentialOffer.objects.create(
        connection_id="1",
        offer_json={
            "offer_key_1": "offer_value_1",
            "offer_key_2": "offer_value_2",
        },
        credential_request=credential_request,
        cred_ex_id="40b771aa-3d77-4171-b8d5-e1da4fcc4620",
        revocation_id=None,
    )


@pytest.fixture
@freeze_time(datetime(2020, 1, 1, tzinfo=timezone.utc))
def second_credential_offer(second_credential_request):
    return CredentialOffer.objects.create(
        connection_id="2",
        offer_json={
            "offer_key_1": "offer_value_1",
            "offer_key_2": "offer_value_2",
        },
        credential_request=second_credential_request,
        cred_ex_id="b4cb054e-5a08-455e-b7a9-fef47d0957e5",
        revocation_id=None,
    )


@pytest.fixture
def connection_invitation(credential_request):
    return ConnectionInvitationFactory(
        connection_id="1", accepted=False, credential_request=credential_request
    )


@pytest.fixture
def conn_invitation_without_cred_request():
    return ConnectionInvitationFactory(connection_id="2", accepted=False, credential_request=None)


@pytest.fixture
def invitation_template():
    name = "invitation"
    return EmailTemplate.objects.create(
        name=name,
        subject="Test UN Digital ID Credential Issuance",
        content="",
        html_content="<html></html>",
    )


@pytest.fixture
def id_manager_create_response():
    response = Response()
    response.status_code = 201
    response.headers = {"Content-Type": "application/json"}
    response._content = (
        b'{"code" : "dd2edf95-39c1-4747-9a72-188860d13c5a","invitation_url" : '
        b'"http://ec2-54-216-73-146.eu-west-1.compute.amazonaws.com:8082'
        b'/deep-link-redirect/dd2edf95-39c1-4747-9a72-188860d13c5a", "id":"1"}'
    )
    return response


@pytest.fixture
def some_organization():
    return Organization.objects.create(name="UNICC")
