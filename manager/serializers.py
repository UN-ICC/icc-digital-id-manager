import base64
import json
import re

import structlog as logging
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty

from manager.handlers import ACAPy
from manager.models import (
    ConnectionInvitation,
    CredentialDefinition,
    CredentialOffer,
    CredentialRequest,
    Organization,
    Schema,
)
from manager.utils import anonymize_values

LOGGER = logging.getLogger(__name__)


class CreatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username"]
        read_only_fields = fields


class SchemaJsonSerializer(serializers.Serializer):
    schema_name = serializers.CharField(required=True)
    schema_version = serializers.CharField(required=True)
    attributes = serializers.ListField(child=serializers.CharField(required=True))


class SchemaSerializer(serializers.ModelSerializer):
    organization_name = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        error_messages={"does_not_exist": "Organization does not exist"},
        source="organization",
        required=True,
        write_only=True,
    )
    schema_json = SchemaJsonSerializer(required=True)
    creator = CreatorSerializer(read_only=True)

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user
        schema = ACAPy().create_schema(validated_data["schema_json"])
        validated_data["schema_id"] = schema.get("schema_id")
        return super(SchemaSerializer, self).create(validated_data)

    class Meta:
        model = Schema
        fields = "__all__"
        read_only_fields = ("organization",)


class CredentialDefinitionSerializer(serializers.ModelSerializer):
    schema = serializers.SlugRelatedField(
        slug_field="schema_id",
        read_only=False,
        queryset=Schema.objects.all(),
        error_messages={"does_not_exist": 'A schema with schema_id "{value}" does not exist'},
    )

    def create(self, validated_data):
        validated_data["creator"] = self.context["request"].user

        credential_definition_upload_result = ACAPy().create_credential_definition(
            {
                "schema_id": validated_data["schema"].schema_id,
                "tag": re.sub(r"\W", "", validated_data["name"]),
                "support_revocation": validated_data["support_revocation"],
                "revocation_registry_size": validated_data["revocation_registry_size"],
            }
        )

        validated_data["credential_id"] = credential_definition_upload_result.get(
            "credential_definition_id"
        )
        return super(CredentialDefinitionSerializer, self).create(validated_data)

    class Meta:
        model = CredentialDefinition

        fields = "__all__"
        read_only_fields = ("creator",)


""" 
Retrieve the followings values for a credential request:
- connection_accepted: bool to check if the connection invitation has been accepted
- credential_offer_accepted: bool to check if the credential offer has been accepted
- connection_invitation_url: encoded url invitation in base64 to be sent to mobile 
and avoid scan QR
"""


class CredentialRequestSerializer(serializers.ModelSerializer):
    credential_definition = None
    cred_def_id = serializers.ReadOnlyField()
    connection_accepted = serializers.SerializerMethodField()
    credential_offer_accepted = serializers.SerializerMethodField()
    connection_invitation_url = serializers.SerializerMethodField()

    def _validate_credential_definition(self, data):
        cred_def_id_or_name = data.get("credential_definition")
        try:
            self.credential_definition = CredentialDefinition.objects.get(
                credential_id=cred_def_id_or_name, enabled=True
            )
        except ObjectDoesNotExist:
            try:
                self.credential_definition = CredentialDefinition.objects.get(
                    name=cred_def_id_or_name, enabled=True
                )
            except Exception:
                LOGGER.error(f"CredentialRequest: credential definition not found: '{data}'")
                raise serializers.ValidationError(
                    {"credential_definition": "Credential definition does not exist"}
                )
        valid_data = data.copy()
        valid_data["credential_definition"] = self.credential_definition.id
        return valid_data

    def _validate_credential_data(self, data):
        schema = set(self.credential_definition.schema.schema_json.get("attributes"))
        try:
            credential_data = json.loads(data.get("credential_data", "{}"))
        except Exception:
            LOGGER.error(
                f"CredentialRequest: {self.credential_definition.credential_id}: "
                f"invalid data: {data.get('credential_data')}"
            )
            raise serializers.ValidationError({"credential_data": "Invalid credential data"})

        credential_data_keys = set(credential_data.keys())
        schema_data_diff = schema - credential_data_keys
        if schema_data_diff:
            LOGGER.error(
                f"CredentialRequest: {self.credential_definition.credential_id}: "
                f"attribute(s) not found in the data provided: {schema_data_diff} - "
                f"definition: '{self.credential_definition.credential_id}' - "
                f"data: {anonymize_values(credential_data)}"
            )
            raise serializers.ValidationError(
                {
                    "credential_data": f"Attribute(s) not found in the data "
                    f"provided: {schema_data_diff}"
                }
            )
        return data

    def run_validation(self, data=empty):
        if data in (empty, None):
            data = {}
        value = self._validate_credential_definition(data)
        value = super().run_validation(value)
        value = self._validate_credential_data(value)
        return value

    def get_connection_accepted(self, obj) -> bool:
        connection_invitation = (
            ConnectionInvitation.objects.filter(credential_request=obj.id)
            .order_by("-created")
            .first()
        )

        return connection_invitation.accepted if connection_invitation else False

    def get_credential_offer_accepted(self, obj) -> bool:
        credential_offer = (
            CredentialOffer.objects.filter(credential_request=obj.id).order_by("-created").first()
        )

        return credential_offer.accepted if credential_offer else False

    def get_connection_invitation_url(self, obj) -> dict:
        connection_invitation = (
            ConnectionInvitation.objects.filter(credential_request=obj.id)
            .order_by("-created")
            .first()
        )

        con_invitation_url = (
            connection_invitation.invitation_json["invitation_url"]
            if connection_invitation
            else None
        )

        return base64.b64encode(bytes(json.dumps(con_invitation_url), "utf-8")).decode("utf-8")

    class Meta:
        model = CredentialRequest

        fields = (
            "cred_def_id",
            "credential_definition",
            "credential_data",
            "code",
            "email",
            "invitation_url",
            "organization",
            "id",
            "revoked_credential",
            "connection_accepted",
            "credential_offer_accepted",
            "connection_invitation_url",
        )
        read_only_fields = ("code", "invitation_url", "id", "revoked_credential")
        extra_kwargs = {
            "credential_definition": {"write_only": True},
            "credential_data": {"write_only": True},
            "email": {"write_only": True},
            "organization": {"write_only": True},
        }


class CredentialOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = CredentialOffer
        fields = "__all__"


class ConnectionInvitationSerializer(serializers.Serializer):
    invitation_json = serializers.JSONField()


class CredentialSerializer(serializers.Serializer):
    connection_id = serializers.CharField()
    cred_def_id = serializers.CharField()
    credential_data = serializers.JSONField()
    credential_definition = None

    def validate_connection_id(self, connection_id):
        try:
            conn_invitation = (
                ConnectionInvitation.objects.filter(connection_id=connection_id)
                .order_by("-created")[:1]
                .get()
            )
        except ConnectionInvitation.DoesNotExist:
            msg = f"Connection id '{connection_id}' not found in ConnectionInvitation"
            LOGGER.error(msg)
            raise ValidationError(msg)

        if not conn_invitation.accepted:
            msg = f"Connection id '{connection_id}' is not accepted"
            LOGGER.error(msg)
            raise ValidationError(msg)

        return connection_id

    def validate_cred_def_id(self, cred_def_id):
        try:
            self.credential_definition = CredentialDefinition.objects.get(
                credential_id=cred_def_id, enabled=True
            )
        except CredentialDefinition.DoesNotExist:
            msg = f"Credential definition '{cred_def_id}' does not exist"
            LOGGER.error(msg)
            raise ValidationError(msg)

        return cred_def_id

    def validate_credential_data(self, credential_data):
        if self.credential_definition is None:
            return credential_data

        schema = set(self.credential_definition.schema.schema_json.get("attributes"))
        credential_data_keys = set(credential_data.keys())
        schema_data_diff = schema - credential_data_keys
        if schema_data_diff:
            msg = (
                f"Attribute(s) not found in the data provided: {schema_data_diff}, "
                f"credential_data given: {credential_data}, cred_def_id: "
                f"'{self.credential_definition.credential_id}'"
            )
            LOGGER.error(msg)
            raise ValidationError(msg)

        return credential_data
