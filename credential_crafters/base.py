class CredentialCrafter:
    def __init__(
        self,
        connection_id: str,
        credential_definition_id: str,
        credential_data: dict,
        *args,
        **kwargs
    ):
        self.connection_id = connection_id
        self.credential_definition_id = credential_definition_id
        self.credential_data = credential_data

    def craft_attributes(self) -> [{}]:
        return [
            {"name": key, "value": value, "mime-type": "text/plain"}
            for key, value in self.credential_data.items()
        ]

    def craft(self) -> {}:
        return {
            "auto_issue": True,
            "auto_remove": False,
            "connection_id": self.connection_id,
            "cred_def_id": self.credential_definition_id,
            "credential_preview": {
                "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/issue-credential"
                "/1.0/credential-preview",
                "attributes": self.craft_attributes(),
            },
        }
