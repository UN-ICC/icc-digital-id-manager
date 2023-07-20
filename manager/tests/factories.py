import factory
from django.contrib.auth.models import User
from faker import Faker

from manager.models import ConnectionInvitation, Organization, Schema

faker = Faker()


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.lazy_attribute(lambda o: faker.unique.user_name())
    email = factory.lazy_attribute(lambda o: f"{o.username}@test.com")
    first_name = factory.lazy_attribute(lambda o: faker.first_name())
    last_name = factory.lazy_attribute(lambda o: faker.last_name())

    class Meta:
        model = User


class OrganizationFactory(factory.django.DjangoModelFactory):
    name = factory.lazy_attribute(lambda o: faker.unique.company())

    class Meta:
        model = Organization


class SchemaFactory(factory.django.DjangoModelFactory):
    name = factory.lazy_attribute(lambda o: f"{faker.unique.company()}-schema")
    creator = factory.SubFactory(UserFactory)
    organization = factory.SubFactory(OrganizationFactory)
    schema_json = {
        "schema_name": "some_schema_name",
        "schema_version": "some_schema_version",
        "attributes": ["schema_key_1", "schema_key_2"],
    }

    class Meta:
        model = Schema


class ConnectionInvitationFactory(factory.django.DjangoModelFactory):
    connection_id = factory.lazy_attribute(lambda o: faker.connection_id())
    accepted = factory.lazy_attribute(lambda o: faker.accepted())
    credential_request = factory.lazy_attribute(lambda o: faker.credential_request())
    invitation_json = {
        "connection_invitation_key_1": "connection_invitation_value_1",
        "connection_invitation_key_2": "connection_invitation_value_2",
        "invitation": {
            "connection_invitation_key_1": "connection_invitation_value_1",
            "connection_invitation_key_2": "connection_invitation_value_2",
        },
        "invitation_url": "invitation.test.url",
    }

    class Meta:
        model = ConnectionInvitation
