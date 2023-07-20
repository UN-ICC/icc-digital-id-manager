import pytest


@pytest.fixture
def aca_connection_invitation():
    return {
        "invitation": {
            "@id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/my-family/1.0/my-message-type",
            "label": "Bob",
            "recipientKeys": ["H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"],
            "imageUrl": "http://192.168.56.101/img/logo.jpg",
            "did": "WgWxqztrNooG92RXvxSTWv",
            "routingKeys": ["H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"],
            "serviceEndpoint": "http://192.168.56.101:8020",
        },
        "invitation_url": "http://192.168.56.101:8020/invite?c_i=eyJAdHlwZSI6Li4ufQ==",
        "connection_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    }
