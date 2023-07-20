import pytest
from rest_framework import status
from rest_framework.test import APIClient


class TestBase:
    __test__ = False
    path = None
    get_data = {}
    put_data = {}
    post_data = {}
    delete_data = {}
    requires_auth = True
    implements_retrieve = False
    implements_create = False
    implements_update = False
    implements_destroy = False

    client = APIClient()

    @pytest.fixture
    def setup(self, setup_method=None):
        return setup_method

    @pytest.fixture
    def authenticate(self, api_client_admin):
        self.client = api_client_admin


class TestGet(TestBase):
    @pytest.fixture
    def get_response(self):
        return self.client.get(
            f"/{self.path}",
            self.get_data,
            format="json",
        )

    def test_get_without_authentication(self, setup, get_response):
        if not self.requires_auth:
            if not self.implements_retrieve:
                returns_status_code_http_405_not_allowed(get_response)
            else:
                returns_status_code_http_200_ok(get_response)
                response_has_etag(get_response)
        else:
            returns_status_code_http_401_unauthorized(get_response)

    def test_get_with_authentication(self, setup, authenticate, get_response):
        if not self.implements_retrieve:
            returns_status_code_http_405_not_allowed(get_response)
        else:
            returns_status_code_http_200_ok(get_response)
            response_has_etag(get_response)


class TestPost(TestBase):
    @pytest.fixture
    def post_response(self):
        return self.client.post(
            path=f"/{self.path}",
            data=self.post_data,
            format="json",
        )

    def test_post_without_authentication(self, setup, post_response):
        returns_status_code_http_401_unauthorized(post_response)

    def test_post_with_authentication(self, setup, authenticate, post_response):
        if self.implements_create:
            returns_status_code_http_201_created(post_response)
        else:
            returns_status_code_http_405_not_allowed(post_response)


class TestPut(TestBase):
    @pytest.fixture
    def put_response(self):
        return self.client.put(
            f"/{self.path}",
            self.put_data,
            format="json",
        )

    def test_put_without_authentication(self, setup, put_response):
        if not self.requires_auth:
            if self.implements_update:
                returns_status_code_http_200_ok(put_response)
            else:
                returns_status_code_http_405_not_allowed(put_response)
        else:
            returns_status_code_http_401_unauthorized(put_response)

    def test_put_with_authentication(self, setup, authenticate, put_response):
        if not self.implements_update:
            returns_status_code_http_405_not_allowed(put_response)
        elif self.requires_auth:
            returns_status_code_http_200_ok(put_response)
        else:
            returns_status_code_http_401_unauthorized(put_response)


class TestDelete(TestBase):
    @pytest.fixture
    def delete_response(self):
        return self.client.delete(f"/{self.path}", self.delete_data, format="json")

    def test_delete_without_authentication(self, setup, delete_response):
        if not self.requires_auth:
            if self.implements_destroy:
                returns_status_code_http_204_no_content(delete_response)
            else:
                returns_status_code_http_405_not_allowed(delete_response)
        else:
            returns_status_code_http_401_unauthorized(delete_response)

    def test_delete_with_authentication(self, setup, authenticate, delete_response):
        if not self.implements_destroy:
            returns_status_code_http_405_not_allowed(delete_response)

        elif self.requires_auth:
            returns_status_code_http_204_no_content(delete_response)
        else:
            returns_status_code_http_401_unauthorized(delete_response)


class TestView(TestGet, TestPost, TestPut, TestDelete):
    __test__ = False
    requires_auth = True


class TestListAPIView(TestView):
    __test__ = False
    implements_retrieve = True
    requires_auth = True


class TestListCreateAPIView(TestView):
    __test__ = False
    implements_retrieve = True
    implements_create = True
    requires_auth = True


class TestListCreateDestroyAPIView(TestView):
    __test__ = False
    implements_retrieve = True
    implements_create = True
    implements_destroy = True
    requires_auth = True


class TestRetrieveAPIView(TestView):
    __test__ = False
    implements_retrieve = True
    requires_auth = True


class TestRetrieveDestroyAPIView(TestView):
    __test__ = False
    implements_retrieve = True
    implements_destroy = True
    requires_auth = True


class TestUnauthenticatedRetrieveAPIView(TestView):
    __test__ = False
    implements_retrieve = True
    requires_auth = False


def returns_status_code_http_200_ok(response):
    assert response.status_code == status.HTTP_200_OK


def returns_status_code_http_404_not_found(response):
    assert response.status_code == status.HTTP_404_NOT_FOUND


def returns_status_code_http_401_unauthorized(response):
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def returns_status_code_http_201_created(response):
    assert response.status_code == status.HTTP_201_CREATED


def returns_status_code_http_204_no_content(response):
    assert response.status_code == status.HTTP_204_NO_CONTENT


def returns_status_code_http_405_not_allowed(response):
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def response_has_etag(response):
    assert response.get("ETag")
