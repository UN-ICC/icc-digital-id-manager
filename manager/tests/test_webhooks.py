from unittest.mock import DEFAULT, call, patch

import pytest
from django.conf import settings
from django.test import override_settings

import manager.views
from manager.tests.api_view_test_classes import (
    TestView,
    returns_status_code_http_200_ok,
    returns_status_code_http_404_not_found,
)


@pytest.fixture
def dependency_mocks():
    return patch.multiple(
        manager.views,
        connection_invitation_accept=DEFAULT,
        credential_offer_create=DEFAULT,
        credential_offer_accept=DEFAULT,
        LOGGER=DEFAULT,
    )


@pytest.mark.django_db
class TestWebhooksAPIView(TestView):
    __test__ = False
    path_base = f"webhooks/{getattr(settings, 'ACA_PY_WEBHOOKS_API_KEY')}/topic"
    test_topic = ""
    path = f"{path_base}/{test_topic}/"

    implements_retrieve = True
    implements_destroy = True
    implements_create = True
    implements_update = True
    requires_auth = False

    @pytest.fixture
    def setup(self, credential_request, mocker):
        self.path = f"{self.path_base}/{self.test_topic}/"
        mocker.patch("time.sleep")
        mocker.patch(
            "manager.views.connection_invitation_accept",
            return_value="mock connection invitation",
        )
        mocker.patch("manager.views.credential_offer_create")
        mocker.patch("manager.views.credential_offer_accept")
        return credential_request

    def test_get_without_authentication(self, setup, get_response):
        returns_status_code_http_200_ok(get_response)

    def test_get_with_authentication(self, setup, authenticate, get_response):
        returns_status_code_http_200_ok(get_response)

    def test_post_without_authentication(self, setup, post_response):
        returns_status_code_http_200_ok(post_response)

    def test_post_with_authentication(self, setup, authenticate, post_response):
        returns_status_code_http_200_ok(post_response)

    def test_delete_without_authentication(self, setup, delete_response):
        returns_status_code_http_200_ok(delete_response)

    def test_delete_with_authentication(self, setup, authenticate, delete_response):
        returns_status_code_http_200_ok(delete_response)

    def test_put_without_authentication(self, setup, put_response):
        returns_status_code_http_200_ok(put_response)

    def test_put_with_authentication(self, setup, authenticate, put_response):
        returns_status_code_http_200_ok(put_response)


@pytest.mark.django_db
class TestWebhooksConnectionsAPIView(TestWebhooksAPIView):
    __test__ = True
    test_topic = "connections"
    message = {"state": "response", "connection_id": "1"}
    get_data = message
    put_data = message
    delete_data = message
    post_data = message

    def test_calls_credential_workflow(self, setup, dependency_mocks, credential_offer):
        with dependency_mocks as mocks:
            mocks["connection_invitation_accept"].return_value = "mock connection invitation"
            response = self.client.post(
                path=f"/{self.path}",
                data=self.post_data,
                format="json",
            )
            returns_status_code_http_200_ok(response)
            mocks["connection_invitation_accept"].assert_called_once_with("1")
            mocks["credential_offer_create"].assert_called_once_with(
                "1", "mock connection invitation"
            )
            mocks["LOGGER"].assert_has_calls(
                [
                    call.info(
                        "webhook: received: topic: 'connections' - state: 'response' - "
                        "message: {'state': 'response', 'connection_id': '1'}"
                    ),
                    call.info("webhook: processing: connection accepted - connection_id: 1"),
                ],
            )

    def test_not_call_credential_offer_workflow(self, setup, dependency_mocks):
        with dependency_mocks as mocks:
            mocks["connection_invitation_accept"].return_value = "mock connection invitation"
            response = self.client.post(
                path=f"/{self.path}",
                data=self.post_data,
                format="json",
            )
            returns_status_code_http_200_ok(response)
            mocks["connection_invitation_accept"].assert_called_once_with("1")
            mocks["credential_offer_create"].assert_not_called()
            mocks["LOGGER"].assert_has_calls(
                [
                    call.info(
                        "webhook: received: topic: 'connections' - state: 'response' - "
                        "message: {'state': 'response', 'connection_id': '1'}"
                    ),
                    call.info("webhook: processing: connection accepted - connection_id: 1"),
                    call.info("webhook: credential_offer not created yet for connection_id: 1"),
                ],
            )

    @override_settings(ACA_PY_WEBHOOKS_API_KEY="keychanged")
    def test_calls_credential_workflow_invalid_token(self, setup, dependency_mocks):
        with dependency_mocks as mocks:
            mocks["connection_invitation_accept"].return_value = "mock connection invitation"
            response = self.client.post(
                path=f"/{self.path}",
                data=self.post_data,
                format="json",
            )
            returns_status_code_http_200_ok(response)
            mocks["connection_invitation_accept"].assert_not_called()
            mocks["credential_offer_create"].assert_not_called()
            mocks["LOGGER"].assert_not_called()

    @override_settings(ACA_PY_WEBHOOKS_API_KEY=None)
    def test_calls_credential_workflow_no_token(self, setup, dependency_mocks):
        self.test_calls_credential_workflow_invalid_token(setup, dependency_mocks)

    def test_id_not_found(self, setup, dependency_mocks):
        post_data = {"state": "response", "connection_id": "7"}
        with dependency_mocks as mocks:
            mocks["connection_invitation_accept"].return_value = None

            response = self.client.post(
                path=f"/{self.path}",
                data=post_data,
                format="json",
            )
            returns_status_code_http_200_ok(response)
            mocks["connection_invitation_accept"].assert_called_once_with("7")
            mocks["credential_offer_create"].assert_not_called()
            mocks["LOGGER"].assert_has_calls(
                [
                    call.info(
                        "webhook: received: topic: 'connections' - state: 'response' - "
                        "message: {'state': 'response', 'connection_id': '7'}"
                    ),
                    call.error("webhook: connection_invitation_accept: connection_id: 7 not found"),
                ]
            )

    def test_invalid_connection_id(self, setup, dependency_mocks):
        post_data = {"state": "response", "connection_id": "random test connection id"}
        with dependency_mocks as mocks:
            mocks["connection_invitation_accept"].return_value = None

            response = self.client.post(
                path=f"/{self.path}",
                data=post_data,
                format="json",
            )
            returns_status_code_http_200_ok(response)
            mocks["connection_invitation_accept"].assert_called_once_with(
                "random test connection id"
            )
            mocks["credential_offer_create"].assert_not_called()
            mocks["LOGGER"].assert_has_calls(
                [
                    call.info(
                        "webhook: received: topic: 'connections' - state: 'response' - "
                        "message: {'state': 'response', "
                        "'connection_id': 'random test connection id'}"
                    ),
                    call.error(
                        "webhook: connection_invitation_accept: connection_id: "
                        "random test connection id not found"
                    ),
                ]
            )

    def test_invalid_state(self, setup, dependency_mocks):
        post_data = {"state": "random test state", "connection_id": "1"}
        with dependency_mocks as mocks:
            response = self.client.post(
                path=f"/{self.path}",
                data=post_data,
                format="json",
            )
            returns_status_code_http_200_ok(response)
            mocks["connection_invitation_accept"].assert_not_called()
            mocks["credential_offer_create"].assert_not_called()
            mocks["LOGGER"].assert_has_calls(
                [
                    call.info(
                        "webhook: received: topic: 'connections' - state: 'random test state' -"
                        " message: {'state': 'random test state', 'connection_id': '1'}"
                    ),
                    call.info(
                        "webhook: topic: connections and state: random test state is invalid"
                    ),
                ]
            )

    def test_malformed_request(self, setup, dependency_mocks):
        post_data = {"malformed": "penguin", "connections": "sarah, michael and jonny"}
        with dependency_mocks as mocks:
            response = self.client.post(
                path=f"/{self.path}",
                data=post_data,
                format="json",
            )
            returns_status_code_http_200_ok(response)
            mocks["connection_invitation_accept"].assert_not_called()
            mocks["credential_offer_create"].assert_not_called()
            mocks["LOGGER"].assert_has_calls(
                [
                    call.info(
                        "webhook: received: topic: 'connections' - state: 'None' - "
                        "message: {'malformed': 'penguin', "
                        "'connections': 'sarah, michael and jonny'}"
                    ),
                    call.info("webhook: topic: connections and state: None is invalid"),
                ]
            )

    def test_webhook_raises_exception(self, setup, mocker):
        response = self.client.post(path=f"/{self.path}", data="invalid_json", format="json")
        returns_status_code_http_200_ok(response)

        mocker.patch("manager.views.connection_invitation_accept", side_effect=Exception())
        response = self.client.post(path=f"/{self.path}", data=self.post_data, format="json")
        returns_status_code_http_200_ok(response)


@pytest.mark.django_db
class TestWebhooksAPIViewWithoutToken(TestWebhooksAPIView):
    __test__ = False

    def test_get_without_authentication(self, setup, get_response):
        returns_status_code_http_404_not_found(get_response)

    def test_get_with_authentication(self, setup, authenticate, get_response):
        returns_status_code_http_404_not_found(get_response)

    def test_post_without_authentication(self, setup, post_response):
        returns_status_code_http_404_not_found(post_response)

    def test_post_with_authentication(self, setup, authenticate, post_response):
        returns_status_code_http_404_not_found(post_response)

    def test_delete_without_authentication(self, setup, delete_response):
        returns_status_code_http_404_not_found(delete_response)

    def test_delete_with_authentication(self, setup, authenticate, delete_response):
        returns_status_code_http_404_not_found(delete_response)

    def test_put_without_authentication(self, setup, put_response):
        returns_status_code_http_404_not_found(put_response)

    def test_put_with_authentication(self, setup, authenticate, put_response):
        returns_status_code_http_404_not_found(put_response)


@pytest.mark.django_db
class TestWebhooksConnectionsAPIViewWithoutToken(TestWebhooksAPIViewWithoutToken):
    __test__ = True
    path_base = "webhooks/topic"
    test_topic = "connections"
    message = {"state": "response", "connection_id": "1"}
    get_data = message
    put_data = message
    delete_data = message
    post_data = message


@pytest.mark.django_db
class TestWebhooksIssueCredentialAPIView(TestWebhooksAPIView):
    __test__ = True
    test_topic = "issue_credential"
    message = {"state": "credential_issued", "connection_id": "1"}

    get_data = message
    put_data = message
    delete_data = message
    post_data = message

    def test_calls_credential_workflow(self, setup, dependency_mocks):
        with dependency_mocks as mocks:
            response = self.client.post(
                path=f"/{self.path}",
                data=self.message,
                format="json",
            )
            returns_status_code_http_200_ok(response)
            mocks["credential_offer_create"].assert_not_called()
            mocks["credential_offer_accept"].assert_called_once_with("1")
            mocks["LOGGER"].assert_has_calls(
                [
                    call.info(
                        "webhook: received: topic: 'issue_credential' - "
                        "state: 'credential_issued' - "
                        "message: {'state': 'credential_issued', 'connection_id': '1'}"
                    ),
                    call.info("webhook: processing: credential accepted - connection_id: 1"),
                ]
            )

    @override_settings(ACA_PY_WEBHOOKS_API_KEY="someothertoken")
    def test_calls_credential_workflow_invalid_token(self, setup, dependency_mocks):
        with dependency_mocks as mocks:
            response = self.client.post(
                path=f"/{self.path}",
                data=self.message,
                format="json",
            )
            returns_status_code_http_200_ok(response)
            mocks["credential_offer_create"].assert_not_called()
            mocks["credential_offer_accept"].assert_not_called()
            mocks["LOGGER"].assert_not_called()

    @override_settings(ACA_PY_WEBHOOKS_API_KEY=None)
    def test_calls_credential_workflow_no_token(self, setup, dependency_mocks):
        self.test_calls_credential_workflow_invalid_token(setup, dependency_mocks)

    def test_connection_id_not_found(self, setup, dependency_mocks):
        post_data = {"state": "credential_issued", "connection_id": "7"}
        with dependency_mocks as mocks:
            mocks["credential_offer_accept"].return_value = None

            response = self.client.post(
                path=f"/{self.path}",
                data=post_data,
                format="json",
            )
            returns_status_code_http_200_ok(response)
            mocks["credential_offer_accept"].assert_called_once_with("7")
            mocks["credential_offer_create"].assert_not_called()
            mocks["LOGGER"].assert_has_calls(
                [
                    call.info(
                        "webhook: received: topic: 'issue_credential' - state: 'credential_issued' "
                        "- message: {'state': 'credential_issued', 'connection_id': '7'}"
                    ),
                    call.error("webhook: credential_offer_accept: connection_id: 7 not found"),
                ]
            )

    def test_malformed_request(self, setup, dependency_mocks):
        post_data = {"malformed": "penguin", "connections": "sarah, michael and jonny"}
        with dependency_mocks as mocks:
            mocks["credential_offer_accept"].return_value = None

            response = self.client.post(
                path=f"/{self.path}",
                data=post_data,
                format="json",
            )

            returns_status_code_http_200_ok(response)

            mocks["credential_offer_accept"].assert_not_called()
            mocks["credential_offer_create"].assert_not_called()
            mocks["LOGGER"].assert_has_calls(
                [
                    call.info(
                        "webhook: received: topic: 'issue_credential' - state: 'None' "
                        "- message: {'malformed': 'penguin', "
                        "'connections': 'sarah, michael and jonny'}"
                    ),
                    call.info("webhook: topic: issue_credential and state: None is invalid"),
                ]
            )

    def test_webhook_raises_exception(self, setup, mocker):
        response = self.client.post(path=f"/{self.path}", data="invalid_json", format="json")
        returns_status_code_http_200_ok(response)

        mocker.patch("manager.views.credential_offer_accept", side_effect=Exception())
        response = self.client.post(path=f"/{self.path}", data=self.post_data, format="json")
        returns_status_code_http_200_ok(response)


@pytest.mark.django_db
class TestWebhooksIssueCredentialAPIViewWithoutToken(TestWebhooksAPIViewWithoutToken):
    __test__ = True
    path_base = "webhooks/topic"
    test_topic = "issue_credential"
    message = {"state": "credential_issued", "connection_id": "1"}
    get_data = message
    put_data = message
    delete_data = message
    post_data = message
