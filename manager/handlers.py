from aca.client import ACAClientFactory
from manager.credential_workflow import connection_invitation_create, is_credential_request_ready
from manager.models import CredentialRequest


class CredentialOfferHandler:
    @classmethod
    def get_credential_offer(cls, code: str) -> (CredentialRequest, str, str):
        credential_request = is_credential_request_ready(code)
        invitation_url, invitation_b64 = "", ""
        connection_invitations = credential_request.connection_invitations.order_by("-created")
        if not connection_invitations or not connection_invitations[0].accepted:
            invitation_url, invitation_b64 = connection_invitation_create(credential_request)
        return credential_request, invitation_b64, invitation_url


class ACAPy:
    def __init__(self):
        self.client = ACAClientFactory.create_client()

    def create_schema(self, schema_json: dict) -> dict:
        return self.client.create_schema(schema_json)

    def create_credential_definition(self, credential_json: dict) -> dict:
        return self.client.create_credential_definition(credential_json)

    def send_revoke_credential(self, credential_json: dict) -> dict:
        return self.client.send_revocation_revoke(credential_json)

    def out_of_band_receive_invitation(self, invitation: dict) -> dict:
        return self.client.out_of_band_receive_invitation(invitation)
    
    def accept_connection_invitation(self, invitation: dict) -> dict:
        return self.client.accept_connection_invitation(invitation)
