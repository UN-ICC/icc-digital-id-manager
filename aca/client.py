import requests
from django.conf import settings


class ACAClient:
    def __init__(self, url: str, transport_url: str, token: str = None) -> None:
        self.url = url
        self.transport_url = transport_url
        self.token = token

        headers = {"accept": "application/json", "Content-Type": "application/json"}
        if self.token:
            headers.update({"X-API-Key": f"{self.token}"})

        self.session = requests.Session()
        self.session.headers.update(headers)

    def get_endpoint_url(self):
        return self.transport_url

    def create_proof_request(self, presentation_request: dict) -> dict:
        response = self.session.post(
            f"{self.url}/present-proof/create-request", json=presentation_request
        )
        response.raise_for_status()
        return response.json()

    def get_public_did(self) -> dict:
        response = self.session.get(f"{self.url}/wallet/did/public")
        response.raise_for_status()
        return response.json()["result"]

    def get_credential_definition(self, cred_def_id: str) -> dict:
        response = self.session.get(f"{self.url}/credential-definitions/{cred_def_id}")
        response.raise_for_status()
        return response.json()["credential_definition"]

    def create_credential_definition(self, cred_def_data: dict) -> dict:
        response = self.session.post(f"{self.url}/credential-definitions", json=cred_def_data)
        response.raise_for_status()
        return response.json()

    def get_schema(self, schema_id: str) -> dict:
        response = self.session.get(f"{self.url}/schemas/{schema_id}")
        response.raise_for_status()
        return response.json()["schema_json"]

    def create_schema(self, schema_data: dict) -> dict:
        response = self.session.post(f"{self.url}/schemas", json=schema_data)
        response.raise_for_status()
        return response.json()

    def create_connection_invitation(self) -> dict:
        response = self.session.post(f"{self.url}/connections/create-invitation")
        response.raise_for_status()
        return response.json()

    def send_credential_offer(self, credential: dict, connection_id: str) -> dict:
        credential.update({"connection_id": connection_id})
        response = self.session.post(f"{self.url}/issue-credential/send-offer", json=credential)
        response.raise_for_status()
        return response.json()

    def retrieve_issue_credential_by_cred_ex_id(self, cred_ex_id: str) -> dict:
        response = self.session.get(f"{self.url}/issue-credential/records/{cred_ex_id}")
        response.raise_for_status()
        return response.json()

    def send_revocation_revoke(self, credential: dict) -> dict:
        response = self.session.post(f"{self.url}/revocation/revoke", json=credential)
        response.raise_for_status()
        return response.json()

    def out_of_band_receive_invitation(self, invitation: dict) -> dict:
        response = self.session.post(f"{self.url}/out-of-band/receive-invitation", json=invitation)
        response.raise_for_status()
        return response.json()
    
    def accept_connection_invitation(self, invitation: dict) -> dict:
        response = self.session.post(f"{self.url}/connections/receive-invitation",  json=invitation)
        response.raise_for_status()
        return response.json()


class ACAClientFactory:
    @staticmethod
    def create_client(*args, **kwargs):
        try:
            token = settings.ACA_PY_AUTH_TOKEN or None
        except Exception:
            token = None
        return ACAClient(settings.ACA_PY_URL, settings.ACA_PY_TRANSPORT_URL, token)
