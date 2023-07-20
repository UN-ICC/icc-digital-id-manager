import json
import time

import structlog as logging
from django.conf import settings
from django.db import transaction
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django_filters.rest_framework import DjangoFilterBackend
from requests import HTTPError
from rest_framework import permissions, status, viewsets
from rest_framework.generics import (
    CreateAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveDestroyAPIView,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from aca.client import ACAClientFactory
from manager.credential_workflow import (
    connection_invitation_accept,
    credential_offer_accept,
    credential_offer_create,
)
from manager.exceptions import ConnectionNotReady
from manager.handlers import ACAPy, CredentialOfferHandler
from manager.models import (
    ConnectionInvitation,
    CredentialDefinition,
    CredentialOffer,
    CredentialRequest,
    Schema,
)
from manager.serializers import (
    ConnectionInvitationSerializer,
    CredentialDefinitionSerializer,
    CredentialOfferSerializer,
    CredentialRequestSerializer,
    CredentialSerializer,
    SchemaSerializer,
)
from manager.utils import EmailHelper, QRCodeHandler

LOGGER = logging.getLogger(__name__)


class SchemaViewSet(viewsets.ModelViewSet):
    serializer_class = SchemaSerializer
    permission_classes = (permissions.IsAuthenticated,)
    queryset = Schema.objects.all()
    http_method_names = ["get", "delete", "put", "post"]
    filterset_fields = ("enabled",)
    search_fields = ("name", "enabled", "creator__username", "organization__name", "schema_id")
    ordering_fields = ("name", "enabled", "organization__name")

    def perform_destroy(self, instance):
        instance.enabled = False
        instance.save()

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.enabled = False
        instance.save()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.create(serializer.validated_data)
        return Response(serializer.data)


class CredentialDefinitionViewSet(viewsets.ModelViewSet):
    serializer_class = CredentialDefinitionSerializer
    permission_classes = (permissions.IsAuthenticated,)
    queryset = CredentialDefinition.objects.all()

    def perform_destroy(self, instance):
        instance.enabled = False
        instance.save()


class CredentialRequestRetrieveDestroyAPIView(RetrieveDestroyAPIView):
    serializer_class = CredentialRequestSerializer
    permission_classes = (permissions.IsAuthenticated,)
    queryset = CredentialRequest.objects.all()

    """
    Soft delete which means:
    - Mark revoked_credential = True (CredentialRequest model)
    - Calls /revocation/revoke endpoint of Aca-Py, only need cred_ex_id value save in 
      CredentialOffer model
    """

    def perform_destroy(self, instance):
        cred_offer = instance.credential_offers.first()

        try:
            ACAPy().send_revoke_credential({"cred_ex_id": cred_offer.cred_ex_id, "publish": True})

            instance.revoked_credential = True
            instance.save()
        except Exception:
            msg = f"Error sending revocation credential for credential request {instance.id}"
            LOGGER.error(msg)
            raise Http404(msg)


class CredentialRequestListCreateAPIView(ListCreateAPIView):
    serializer_class = CredentialRequestSerializer
    permission_classes = (permissions.IsAuthenticated,)
    queryset = CredentialRequest.objects.all()

    def get_serializer(self, *args, **kwargs):
        if isinstance(kwargs.get("data", {}), list):
            kwargs["many"] = True
        return super(CredentialRequestListCreateAPIView, self).get_serializer(*args, **kwargs)

    @staticmethod
    def create_one(instance: CredentialRequest, request: HttpRequest):
        code = instance.code
        try:
            _, invitation_b64, credential_offer_url = CredentialOfferHandler.get_credential_offer(
                code
            )
        except RuntimeError:
            msg = f"Credential already accepted - code:{code}"
            LOGGER.error(msg)
            raise Http404(msg)
        except CredentialRequest.DoesNotExist:
            msg = f"There is not credential request with code:{code}"
            LOGGER.error(msg)
            raise Http404(msg)
        except Exception:
            LOGGER.error("Unexpected error", exc_info=True)
            raise Http404()

        qr_code_img = QRCodeHandler.text_to_qr(credential_offer_url)
        EmailHelper.send(
            instance.email,
            template="invitation",
            context={
                "credential_name": instance.credential_definition.name,
                "qr_code_img": qr_code_img,
                "deep_link_redirect": request.build_absolute_uri(
                    reverse("deep_link_redirect", args=[code])
                ),
                "base_url": settings.SITE_URL,
            },
        )

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

        try:
            self.create_one(serializer.instance, request=self.request)

        except AttributeError:
            for credential_request in serializer.instance:
                self.create_one(credential_request, request=self.request)


class CredentialOfferListAPIView(ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = CredentialOfferSerializer
    queryset = CredentialOffer.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ["credential_request"]

    """ 
    Calls /issue-credential/records/{cred_ex_id} endpoint of Aca-Py, 
    to retrieve revocation_id and credential_id values 
    """

    def get(self, request, *args, **kwargs):
        cred_req_id = request.query_params.get("credential_request")

        if cred_req_id is None:
            return super().get(request)

        cred_offer = CredentialOffer.objects.filter(credential_request__id=cred_req_id).first()
        aca_client = ACAClientFactory.create_client()
        response = aca_client.retrieve_issue_credential_by_cred_ex_id(cred_offer.cred_ex_id)

        CredentialOffer.objects.filter(id=cred_offer.id).update(
            revocation_id=response.get("revocation_id"),
            credential_id=response.get("credential_id"),
        )

        return super().get(request)


class DeepLinkRedirect(APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request, code):
        _, invitation_b64, _ = CredentialOfferHandler.get_credential_offer(code)
        deep_link = f"didcomm://launch?c_i={invitation_b64}"
        HttpResponseRedirect.allowed_schemes.append("didcomm")  # Allow redirection to this protocol
        return redirect(deep_link)


class ConnectionInvitationView(CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ConnectionInvitationSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invitation_json = dict(serializer.validated_data["invitation_json"])

        try:
            aca_client = ACAClientFactory.create_client()
            aca_accepted_connection = aca_client.accept_connection_invitation(invitation_json)
            connection_id = aca_accepted_connection["connection_id"]
            ConnectionInvitation.objects.create(
                connection_id=connection_id,
                invitation_json=invitation_json,
                accepted=True,
            )
        except Exception as error:
            msg = f"Error establishing connection, error: {error}"
            LOGGER.error(msg)
            return Response(msg, status=status.HTTP_400_BAD_REQUEST)

        return Response({"connection_id": connection_id}, status=status.HTTP_201_CREATED)


class CredentialView(CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = CredentialSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cred_def_id = serializer.validated_data["cred_def_id"]
        credential_data = serializer.validated_data["credential_data"]
        cred_request = self._create_credential_request(cred_def_id, credential_data)

        connection_id = serializer.validated_data["connection_id"]
        connection_invitation = self._update_connection_invitation(connection_id, cred_request)

        try:
            aca_credential_offer = credential_offer_create(connection_id, connection_invitation)
        except HTTPError as error:
            raise ConnectionNotReady(error.response.text)

        response = {
            "connection_id": aca_credential_offer.get("connection_id"),
            "cred_def_id": aca_credential_offer.get("cred_def_id"),
            "cred_request_id": cred_request.id,
        }
        return Response(response, status=status.HTTP_201_CREATED)

    def _create_credential_request(
        self, cred_def_id: str, credential_data: dict
    ) -> CredentialRequest:
        cred_definition = CredentialDefinition.objects.get(credential_id=cred_def_id)

        return CredentialRequest.objects.create(
            credential_definition=cred_definition,
            credential_data=credential_data,
            creator=self.request.user,
        )

    def _update_connection_invitation(
        self, connection_id: str, cred_request: CredentialRequest
    ) -> ConnectionInvitation:
        connection_invitation = (
            ConnectionInvitation.objects.filter(connection_id=connection_id)
            .order_by("-created")[:1]
            .get()
        )

        if connection_invitation.credential_request is None:
            connection_invitation.credential_request = cred_request
            connection_invitation.save()

            return connection_invitation
        else:
            new_conection_invitation = ConnectionInvitation.objects.create(
                connection_id=connection_invitation.connection_id,
                invitation_json=connection_invitation.invitation_json,
                accepted=True,
                credential_request=cred_request,
            )
            return new_conection_invitation


@csrf_exempt
def webhooks(request, api_key, topic):
    if not api_key == getattr(settings, "ACA_PY_WEBHOOKS_API_KEY"):
        LOGGER.info(
            f"webhook: {topic} : unauthorized request: '{request.body}' - invalid api key supplied"
        )
        return HttpResponse()

    try:
        message = json.loads(request.body)

        state = message.get("state")

        LOGGER.info(f"webhook: received: topic: '{topic}' - state: '{state}' - message: {message}")

        if topic == "connections" and state == "response":
            connection_id = message.get("connection_id")
            try:
                connection_invitation = connection_invitation_accept(connection_id)
                if connection_invitation:
                    LOGGER.info(
                        f"webhook: processing: connection accepted - connection_id: {connection_id}"
                    )

                    try:
                        CredentialOffer.objects.get(connection_id=connection_id)

                        time.sleep(5)
                        credential_offer_create(connection_id, connection_invitation)
                    except CredentialOffer.DoesNotExist:
                        LOGGER.info(
                            f"webhook: credential_offer not created yet for connection_id:"
                            f" {connection_id}"
                        )
                else:
                    LOGGER.error(
                        f"webhook: connection_invitation_accept: connection_id: "
                        f"{connection_id} not found"
                    )
            except Exception as e:
                LOGGER.error(
                    f"webhook: connection_accepted: connection_id: {connection_id} - error: {e}"
                )

        elif topic == "issue_credential" and state == "credential_issued":
            connection_id = message.get("connection_id")
            try:
                accepted_credential_offer = credential_offer_accept(connection_id)
                if accepted_credential_offer:
                    LOGGER.info(
                        f"webhook: processing: credential accepted - connection_id: {connection_id}"
                    )

                else:
                    LOGGER.error(
                        f"webhook: credential_offer_accept: connection_id: "
                        f"{connection_id} not found"
                    )

            except Exception as e:
                LOGGER.error(
                    f"webhook: issue_credential: connection_id: {connection_id} - error: {e}"
                )
        else:
            LOGGER.info(f"webhook: topic: {topic} and state: {state} is invalid")

    except Exception as e:
        LOGGER.info(f"webhook: {topic} : bad request: '{request.body}' - {e}")

    return HttpResponse()
