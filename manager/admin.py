from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.safestring import mark_safe

from manager.handlers import ACAPy
from manager.models import (
    ConnectionInvitation,
    CredentialDefinition,
    CredentialOffer,
    CredentialRequest,
    Organization,
    Schema,
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Schema)
class SchemaAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "schema_id", "enabled", "creator", "organization", "created")
    list_display_links = ("id",)
    list_filter = ("enabled", "organization")
    search_fields = (
        "creator__username",
        "creator__first_name",
        "creator__last_name",
        "name",
        "schema_json",
    )

    change_form_template = "schema_changeform.html"

    def response_change(self, request, obj):
        if "_upload-schema" in request.POST:
            self.upload_schema(obj)
            return HttpResponseRedirect(".")

        return super().response_change(request, obj)

    def upload_schema(self, instance):
        instance.schema_id = ACAPy().create_schema(instance.schema_json).get("schema_id")
        instance.save()


@admin.register(CredentialDefinition)
class CredentialDefinitionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "credential_id",
        "schema",
        "enabled",
        "support_revocation",
        "creator",
        "created",
    )
    list_display_links = ("id",)
    list_filter = (
        "enabled",
        "support_revocation",
    )
    search_fields = (
        "creator__username",
        "creator__first_name",
        "creator__last_name",
        "name",
    )

    change_form_template = "credentialdefinition_changeform.html"

    def response_change(self, request, obj):
        if "_upload-cred-def" in request.POST:
            self.upload_cred_def(obj)
            return HttpResponseRedirect(".")

        return super().response_change(request, obj)

    def upload_cred_def(self, instance):
        instance.credential_id = (
            ACAPy()
            .create_credential_definition(instance.credential_json())
            .get("credential_definition_id")
        )
        instance.save()


@admin.register(CredentialRequest)
class CredentialRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "credential_definition",
        "code",
        "email",
        "invitation_url",
        "connection",
        "credential",
        "revoked_credential",
        "creator",
        "created",
        "modified",
        "organization",
    )
    list_display_links = ("id",)
    list_filter = (
        "credential_definition",
        "organization",
    )
    readonly_fields = [
        "revoked_credential",
    ]
    search_fields = (
        "organization",
        "credential_data",
        "creator__username",
        "creator__first_name",
        "creator__last_name",
        "credential_definition__name",
        "credential_definition__credential_id",
    )
    actions = ["revoke_credential_request"]

    @admin.action(description="Revoke credential request")
    def revoke_credential_request(self, request, queryset):
        for cred_request in queryset:
            cred_offer = cred_request.credential_offers.first()

            try:
                ACAPy().send_revoke_credential(
                    {"cred_ex_id": cred_offer.cred_ex_id, "publish": True}
                )
                cred_request.revoked_credential = True
                cred_request.save()
                self.message_user(request, "Credential request revoked", messages.SUCCESS)

            except Exception:
                cred_request.revoked_credential = False
                cred_request.save()
                self.message_user(request, "Error revoking credential request", messages.ERROR)

    def connection(self, item):
        connection_invitation = item.connection_invitations.order_by("-created").first()
        return connection_invitation.accepted if connection_invitation else False

    def credential(self, item):
        credential_offer = item.credential_offers.order_by("-created").first()
        return credential_offer.accepted if credential_offer else False

    connection.boolean = True
    credential.boolean = True


@admin.register(ConnectionInvitation)
class ConnectionInvitationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "connection_id",
        "credential_request_link",
        "accepted",
        "created",
        "modified",
    )
    list_display_links = ("id",)
    list_filter = ("accepted",)
    search_fields = ("connection_id",)

    def credential_request_link(self, item):
        if item.credential_request is None:
            return None

        url = reverse("admin:manager_credentialrequest_change", args=[item.credential_request.id])
        link = f'<a href="{url}">{item.credential_request}</a>'
        return mark_safe(link)

    credential_request_link.short_description = "Credential Request"


@admin.register(CredentialOffer)
class CredentialOfferAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "connection_id",
        "credential_request",
        "accepted",
        "created",
        "modified",
    )
    list_display_links = ("id",)
    list_filter = ("accepted",)
    search_fields = ("connection_id",)
