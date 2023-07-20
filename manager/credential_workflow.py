import base64
import json

import structlog as logging

from aca.client import ACAClientFactory
from manager.models import ConnectionInvitation, CredentialOffer, CredentialRequest
from manager.utils import get_credential_crafter_class

LOGGER = logging.getLogger(__name__)


def connection_invitation_accept(connection_id: str) -> ConnectionInvitation:
    try:
        return _step_accept(ConnectionInvitation, connection_id)
    except Exception as e:
        LOGGER.error(f"connection_invitation_accept: connection_id: {connection_id} - error: {e}")


def credential_offer_accept(connection_id: str) -> CredentialOffer:
    try:
        return _step_accept(CredentialOffer, connection_id)
    except Exception as e:
        LOGGER.error(f"credential_offer_accept: connection_id: {connection_id} - error: {e}")


def _step_accept(model_class, connection_id: str):
    model = model_class.objects.filter(connection_id=connection_id).order_by("-created").first()
    if not model:
        raise RuntimeError(f"Not found: {model_class} with connection_id: {connection_id}")
    model.accepted = True
    model.save()
    return model


def connection_invitation_create(credential_request: CredentialRequest) -> (str, str):
    connection_invitation_not_accepted = (
        credential_request.connection_invitations.filter(accepted=False)
        .order_by("-created")
        .first()
    )
    if connection_invitation_not_accepted:
        aca_connection_invitation = connection_invitation_not_accepted.invitation_json
    else:
        aca_client = ACAClientFactory.create_client()
        aca_connection_invitation = aca_client.create_connection_invitation()
        ConnectionInvitation.objects.create(
            connection_id=aca_connection_invitation["connection_id"],
            invitation_json=aca_connection_invitation,
            credential_request=credential_request,
        )

    invitation_b64 = base64.b64encode(
        bytes(json.dumps(aca_connection_invitation["invitation"]), "utf-8")
    ).decode("utf-8")
    invitation_url = aca_connection_invitation[
        "invitation_url"
    ]  # f"{settings.ACA_PY_URL}?c_i={invitation_b64}"

    return invitation_url, invitation_b64


def credential_offer_create(
    connection_id: str, connection_invitation: ConnectionInvitation
) -> dict:
    credential_definition_id = (
        connection_invitation.credential_request.credential_definition.credential_id
    )
    credential_crafter_class = get_credential_crafter_class(credential_definition_id)
    credential_crafter = credential_crafter_class(
        connection_id=connection_id,
        credential_definition_id=credential_definition_id,
        credential_data=connection_invitation.credential_request.credential_data,
    )
    aca_credential_offer = credential_crafter.craft()
    aca_client = ACAClientFactory.create_client()
    response_cred_offer = aca_client.send_credential_offer(aca_credential_offer, connection_id)

    CredentialOffer.objects.create(
        connection_id=connection_id,
        offer_json=aca_credential_offer,
        credential_request=connection_invitation.credential_request,
        cred_ex_id=response_cred_offer["credential_exchange_id"],
        revocation_id=response_cred_offer.get("revocation_id"),
        credential_id=response_cred_offer.get("credential_id"),
    )

    return aca_credential_offer


def is_credential_request_ready(code: str) -> CredentialRequest:
    credential_request = CredentialRequest.objects.get(code=code)
    credential_offers = credential_request.credential_offers.order_by("-created")
    if credential_offers and credential_offers[0].accepted is True:
        raise RuntimeError(f"Credential already accepted - code:{code}")
    return credential_request
