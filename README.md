# UN Digital ID - ID Manager

This piece is in charge of:

* Manage and keep track of which Schemas and Credential Definition an organization works with
* Expose an Endpoint to create a Credential, providing:
  * Type of credential (credential_definition_id)
  * Email where to send the invitation
  * Data to create the credential with
* Send an email with a 'secret' link, to a page where a connection invitation is displayed (QR and deep link)
* Consuming the invitation with the Digital ID app triggers the following process:
  1. A connection is created (if accepted by the user) between the App and de APA-py of the organization that offered the credential
  1. A credential offer is sent from the ACA-py to the app and, if accepted, the credential is stored in the user's wallet
  1. While all this happens, the page is polling periodically to update the process status and display informative messages

## Dependencies

The project depends on:
- PostgreSQL database and a running instance of [ACA-PY](https://github.com/hyperledger/aries-cloudagent-python).
- Local Deployment a VON Network: [Guide Developing Hyperledger applications](https://unicc.atlassian.net/wiki/spaces/CPS/pages/4479057927/Developing+Hyperledger+applications)

## How to define an env variable?

```
.env
``` 
Note, it's not under version control and other users will not see your changes. 
Use env.example to add new env variable, other users will copy env.example to .env. later.

If you dont use docker-compose, use:
```
$ export $(cat .env | xargs)
```

to export these variables

## Running the project

Specify in the settings:

* DB config
* Email config
* Credential crafters (see [Credential crafters](credential_crafters))
* ACA-py location
* Public website (accessible from the internet) url
* Apply migrations: make migrate
* Create super user: make createsuperuser
* Run: make start or make start_with_db

Access the admin at `http://localhost:8082/admin` and:

1. Create a Token for your user
1. Create a Schema in the Schemas section of the admin. Example:
    - name: (choose a name)
    - schema_id: (leave it blank, will be filled when uploaded to Blockchain)
    - creator: (select the creator user for the schema)
    - schema_json: 
```json
{
  "schema_version": "1.0",
  "schema_name": "prefs",
  "attributes": [
    "score"
  ]
}
```
*Click 'Save and continue editing' and, after that, 'Upload to Blockchain'* 
``

1. Create a Credential Definition in the Credential Definitions section of the admin (the `schema_id` must
match one of your existing Schema's). Example:

    - name: (choose a name)
    - credential_id: (leave it blank, will be filled when uploaded to Blockchain)
    - creator: (select the creator user for the schema)
    - schema: (select one, you should put its `schema_id` in the `credential_json` object)
    - credential_json:
```json
{
  "tag": "default",
  "support_revocation": false,
  "schema_id": "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0",
  "revocation_registry_size": 0
}
```

    
*Click 'Save and continue editing' and, after that, 'Upload to Blockchain'*

1. Now make a request to the REST API to start the credential issuance workflow (the `credentia_definition` parameter
should be the `credential_id` of some existing Credential Definition):

```
curl --location --request POST 'http://localhost:8082/credential-request' \
--header 'Authorization: token your_token' \
--header 'Content-Type: application/json' \
--data-raw '{
    "credential_definition": "Th7MpTaRZVRYnPiabds81Y:3:CL:16:default",
    "email": "your_email@mail.com",
    "credential_data": "{ \"score\": \"10\" }"
}'
```


1. You should receive an email with a link you should click to start the workflow (alternatively you can find
  the invitation link in the admin, under 'Credential requests')

## Credential crafters

You might have special needs regarding the process of creating the credential offer in the blockchain from the
provided data via the API. This process is handled via `CredentialCrafters`: simple classes that
'craft' a valid ACA-py credential offer from the provided data, the connection id and the credential definition id.
This applicaton is shipped with a base CredentialCrafter (`credential_crafters.base.CredentialCrafter`) that
simply takes all the data provided and translates them as `text` attributes of the credential offer. In order
to customize this process, you should:

- Create yor own Credential Crafter class extending from `credential_crafters.base.CredentialCrafter`
- Override the `craft_attributes()` method with your own logic, returning a list of dictionaires with a valid
  ACA-py `credential_preview`: `[{"name": "n", "value": "v", "mime-type": "text/plain"}, ...]`, having available
  the following class attributes: - credential_data - credential_definition_id - connection_id
- Configure it in the django settings as follows:

```
CREDENTIAL_CRAFTERS = {
    "credential_definition_id": "module.CrafterClass"
}
```

For example:

```
CREDENTIAL_CRAFTERS = {
    "Th7MpTaRZVRYnPiabds81Y:3:CL:16:default": "credential_crafters.my_module.MyCredentialCrafter"
}
```

(The generic crafter does not need to be specified in that config)


# Running an ACA-PY

Please, check the docs on how to [install](https://github.com/hyperledger/aries-cloudagent-python#install) and 
[run](https://github.com/hyperledger/aries-cloudagent-python/blob/master/DevReadMe.md#running) and ACA-py. 


Important settings to specify:
- `--endpoint`: Public url, accessible to clients
- `--webhook-url`: url where to send the ACA-PY events for the ID Manager, should be: `id_managet_url/webhooks`
- `--auto-verify-presentation`, `--auto-accept-requests`, `--auto-ping-connection`


- Optional:
- `--invite --invite-multi-use`: Create re-usable invitations to use with apps such as the [aries-toolbox](https://github.com/hyperledger/aries-toolbox).
- `--plugin acapy_plugin_toolbox`: Add functionalities for the [aries-toolbox](https://github.com/hyperledger/aries-toolbox).

Example:

```
aca-py start 
--seed 000000000000000000000000Steward1 
--inbound-transport http 0.0.0.0 8002 \
--outbound-transport http \
--admin 0.0.0.0 4002 \
--admin-insecure-mode \
--wallet-type indy \
--wallet-name aca-idmanager \
--wallet-key '123456' \
--auto-ping-connection \
--auto-respond-messages \
--auto-verify-presentation \
--genesis-url http://${DOCKERHOST}:9000/genesis \
--log-level INFO \
--auto-accept-requests \
--plugin acapy_plugin_toolbox \
--endpoint http://ec2-54-76-115-219.eu-west-1.compute.amazonaws.com:8002 \
--auto-provision \
--webhook-url http://ec2-54-76-115-219.eu-west-1.compute.amazonaws.com:8082/webhooks
```

## How to run tests

```
$ make tests
```

## How to run formatters, linters, etc.

```
$ make lint
$ make black
$ make isort
```

## Available commands

```
$ make help
```

