import re
import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django_extensions.db.fields.json import JSONField
from model_utils.models import TimeStampedModel


class Organization(models.Model):
    name = models.CharField(max_length=100, primary_key=True)

    def __str__(self):
        return self.name


class Schema(TimeStampedModel):
    name = models.CharField(max_length=50)
    schema_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    enabled = models.BooleanField(default=True)
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="schemas",
    )
    organization = models.ForeignKey(
        Organization, null=True, related_name="schemas", on_delete=models.CASCADE
    )
    schema_json = JSONField()

    def __str__(self):
        if self.schema_id:
            return "{0}:{1}".format(self.name, self.schema_id)

        return "{0}:".format(self.name)

    class Meta:
        ordering = ("-created",)


class CredentialDefinition(TimeStampedModel):
    name = models.CharField(max_length=50, unique=True)
    credential_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    schema = models.ForeignKey(
        Schema,
        on_delete=models.CASCADE,
        limit_choices_to={"schema_id__isnull": False},
    )
    enabled = models.BooleanField(default=True)
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="credential_definitions",
    )
    support_revocation = models.BooleanField(default=True)
    revocation_registry_size = models.IntegerField(default=100)

    def credential_json(self):
        return {
            "schema_id": self.schema.schema_id,
            "tag": re.sub(r"\W", "", self.name.lower()),
            "support_revocation": self.support_revocation,
            "revocation_registry_size": self.revocation_registry_size,
        }

    def __str__(self):
        if self.credential_id:
            return "{0}:{1}".format(self.name, self.credential_id)

        return "{0}:".format(self.name)

    class Meta:
        ordering = ("-created",)


class CredentialRequest(TimeStampedModel):
    code = models.CharField(max_length=36, default=uuid.uuid4, unique=True)
    credential_definition = models.ForeignKey(
        CredentialDefinition,
        on_delete=models.CASCADE,
        related_name="credential_requests",
        limit_choices_to={"credential_id__isnull": False},
    )
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="credential_requests",
    )
    credential_data = JSONField()
    email = models.EmailField(blank=None, null=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)
    revoked_credential = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.code}"

    @property
    def invitation_url(self):
        return f"{settings.SITE_URL}/deep-link-redirect/{self.code}"

    @property
    def connection_invitation_polling_url(self):
        return f"{settings.SITE_URL}/connection-check?code={self.code}"

    @property
    def credential_offer_polling_url(self):
        return f"{settings.SITE_URL}/credential-check?code={self.code}"

    @property
    def cred_def_id(self):
        return self.credential_definition.credential_id

    class Meta:
        ordering = ("-created",)


class ConnectionInvitation(TimeStampedModel):
    connection_id = models.CharField(max_length=100)
    invitation_json = JSONField()
    accepted = models.BooleanField(default=False)
    credential_request = models.ForeignKey(
        CredentialRequest,
        on_delete=models.CASCADE,
        related_name="connection_invitations",
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"Conn:{self.connection_id}-accepted:{self.accepted}"


class CredentialOffer(TimeStampedModel):
    connection_id = models.CharField(max_length=100)
    offer_json = JSONField()
    accepted = models.BooleanField(default=False)
    credential_request = models.ForeignKey(
        CredentialRequest,
        on_delete=models.CASCADE,
        related_name="credential_offers",
    )
    cred_ex_id = models.CharField(max_length=250, null=True)
    revocation_id = models.CharField(max_length=250, null=True)
    credential_id = models.CharField(max_length=250, null=True)

    def __str__(self):
        return f"Offer:{self.connection_id}-accepted:{self.accepted}"
