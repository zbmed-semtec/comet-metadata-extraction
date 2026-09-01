from typing import Optional
from pydantic import BaseModel, Field


class Person(BaseModel):
    name: Optional[str] = None
    givenName: Optional[str] = None
    familyName: Optional[str] = None
    email: Optional[str] = None
    url: Optional[str] = None
    atId: Optional[str] = Field(default=None, serialization_alias="@id")

    def toJsonLdDict(self):
        helper = self.model_dump(by_alias=True)
        helper.update({
            "@context": "https://schema.org",
            "@type": "Person",
        })
        result = {key:value for key, value in helper.items() if value is not None}
        return result