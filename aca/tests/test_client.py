import pytest
from requests import Session, exceptions

from aca.client import ACAClient


class TestAcaClient:
    url = "http://127.0.0.1"
    client = ACAClient(url, url, "token")

    def test_init_with_token(self):
        client_with_token = ACAClient("url", "transport_url", "token")
        assert client_with_token.url == "url"
        assert client_with_token.transport_url == "transport_url"
        assert client_with_token.token == "token"
        assert type(client_with_token.session) == Session
        assert client_with_token.session.headers == {
            "User-Agent": "python-requests/2.28.1",
            "Accept-Encoding": "gzip, deflate",
            "Accept": "*/*",
            "Connection": "keep-alive",
            "accept": "application/json",
            "Content-Type": "application/json",
            "X-API-Key": "token",
        }

    def test_init_without_token(self):
        client_without_token = ACAClient("url", "transport_url")
        assert client_without_token.url == "url"
        assert client_without_token.transport_url == "transport_url"
        assert not client_without_token.token
        assert client_without_token.session.headers == {
            "User-Agent": "python-requests/2.28.1",
            "Accept-Encoding": "gzip, deflate",
            "Accept": "*/*",
            "Connection": "keep-alive",
            "accept": "application/json",
            "Content-Type": "application/json",
        }

    def test_get_endpoint_url(self):
        result = self.client.get_endpoint_url()
        assert result == self.url

    def test_create_proof_request(self, requests_mock):
        mock_result = {"result": 0}
        requests_mock.post(f"{self.url}/present-proof/create-request", json=mock_result)
        result = self.client.create_proof_request({})
        assert result == mock_result

    def test_get_public_did(self, requests_mock):
        mock_result = {"result": 0}
        requests_mock.get(f"{self.url}/wallet/did/public", json=mock_result)
        result = self.client.get_public_did()
        assert result == 0

    def test_get_credential_definition(self, requests_mock):
        mock_result = {"definition": 0}
        requests_mock.get(
            f"{self.url}/credential-definitions/some_def_id",
            json={"credential_definition": mock_result},
        )
        result = self.client.get_credential_definition("some_def_id")
        assert result == mock_result

    def test_get_schema(self, requests_mock):
        mock_result = {"schema": 0}
        requests_mock.get(f"{self.url}/schemas/some_schema_id", json={"schema_json": mock_result})
        result = self.client.get_schema("some_schema_id")
        assert result == mock_result

    def test_create_connection_invitation(self, requests_mock):
        mock_result = {"invitation": 0}
        requests_mock.post(f"{self.url}/connections/create-invitation", json=mock_result)
        result = self.client.create_connection_invitation()
        assert result == mock_result

    def test_send_credential_offer(self, requests_mock):
        mock_result = {
            "connection_id": "some_connection_id",
            "offer_json": {},
            "credential_request": {},
        }
        requests_mock.post(f"{self.url}/issue-credential/send-offer", json=mock_result)
        result = self.client.send_credential_offer({}, "some_connection_id")
        assert result == mock_result

    def test_retrieve_issue_credential_by_cred_ex_id(self, requests_mock):
        cred_ex_id = "8fc004fa-015c-45a7-8aac-e6111c605ad9"
        mock_result = {
            "connection_id": "e8433f39-f7dc-45a6-9576-4bfa21beb514",
            "credential_exchange_id": cred_ex_id,
            "revocation_id": "13",
        }
        requests_mock.get(f"{self.url}/issue-credential/records/{cred_ex_id}", json=mock_result)
        result = self.client.retrieve_issue_credential_by_cred_ex_id(cred_ex_id)
        assert result == mock_result

    def test_create_credential_definition(self, requests_mock):
        requests_mock.post(f"{self.url}/credential-definitions", json={"mock": "result"})
        result = self.client.create_credential_definition({"some": "data"})
        assert result == {"mock": "result"}

    def test_create_credential_definition_raises_error(self, requests_mock):
        requests_mock.post(
            f"{self.url}/credential-definitions",
            status_code=500,
            text="500 Internal Server Error Server got itself in trouble",
        )
        with pytest.raises(exceptions.HTTPError):
            self.client.create_credential_definition({"some": "data"})

    def test_create_schema(self, requests_mock):
        requests_mock.post(f"{self.url}/schemas", json={"mock": "result"})
        result = self.client.create_schema({"some": "data"})
        assert result == {"mock": "result"}

    def test_create_schema_raises_error(self, requests_mock):
        requests_mock.post(
            f"{self.url}/schemas",
            status_code=500,
            text="500 Internal Server Error Server got itself in trouble",
        )
        with pytest.raises(exceptions.HTTPError):
            self.client.create_schema({"some": "data"})

    def test_send_revocation_revoke(self, requests_mock):
        requests_mock.post(f"{self.url}/revocation/revoke", json={})
        result = self.client.send_revocation_revoke({"some": "data"})
        assert result == {}

    def test_send_revocation_revoke_raises_error(self, requests_mock):
        requests_mock.post(
            f"{self.url}/revocation/revoke",
            status_code=500,
            text="500 Internal Server Error Server got itself in trouble",
        )
        with pytest.raises(exceptions.HTTPError):
            self.client.send_revocation_revoke({"some": "data"})

    def test_out_of_band_receive_invitation(self, requests_mock):
        requests_mock.post(f"{self.url}/out-of-band/receive-invitation", json={"mock": "result"})
        result = self.client.out_of_band_receive_invitation({"some": "data"})
        assert result == {"mock": "result"}

    def test_accept_connection_invitation(self, requests_mock):
        requests_mock.post(f"{self.url}/connections/receive-invitation", json={"mock": "result"})
        result = self.client.accept_connection_invitation({"some": "data"})
        assert result == {"mock": "result"}