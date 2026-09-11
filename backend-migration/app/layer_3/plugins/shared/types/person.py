from typing import Optional
from pydantic import Field
from app.layer_3.plugins.shared.types.json_ld_serializable import JsonLdSerializable
from app.layer_3.plugins.shared.types.organization import Organization
from app.layer_3.plugins.shared.types.online_account import OnlineAccount

class Person(JsonLdSerializable):
    name: Optional[str] = None
    givenName: Optional[str] = None
    familyName: Optional[str] = None
    email: Optional[list[str] | str] = None
    url: Optional[str] = None
    atId: Optional[str] = Field(default=None, serialization_alias="@id")
    affiliation: Optional[Organization] = None
    account: Optional[OnlineAccount] = None
    sameAs: Optional[str] = None