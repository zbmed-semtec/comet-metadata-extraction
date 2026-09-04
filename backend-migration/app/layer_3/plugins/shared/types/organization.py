from datetime import date
from typing import List, Optional, Union
from pydantic import HttpUrl
from app.layer_3.plugins.shared.types.json_ld_serializable import JsonLdSerializable

class Organization(JsonLdSerializable):
    # Properties from Organization
    acceptedPaymentMethod: Optional[Union[str, List[str]]] = None
    actionableFeedbackPolicy: Optional[Union[str, HttpUrl]] = None
    address: Optional[Union[str, dict]] = None
    agentInteractionStatistic: Optional[Union[dict, List[dict]]] = None
    aggregateRating: Optional[dict] = None
    alumni: Optional[Union[dict, List[dict]]] = None
    areaServed: Optional[Union[str, dict, List[Union[str, dict]]]] = None
    award: Optional[Union[str, List[str]]] = None
    brand: Optional[Union[dict, "Organization"]] = None
    companyRegistration: Optional[Union[dict, List[dict]]] = None
    contactPoint: Optional[Union[dict, List[dict]]] = None
    correctionsPolicy: Optional[Union[str, HttpUrl]] = None
    department: Optional[Union["Organization", List["Organization"]]] = None
    dissolutionDate: Optional[date] = None
    diversityPolicy: Optional[Union[str, HttpUrl]] = None
    diversityStaffingReport: Optional[Union[dict, HttpUrl]] = None
    duns: Optional[str] = None
    email: Optional[str] = None
    employee: Optional[Union[dict, List[dict]]] = None
    ethicsPolicy: Optional[Union[str, HttpUrl]] = None
    event: Optional[Union[dict, List[dict]]] = None
    faxNumber: Optional[str] = None
    founder: Optional[Union["Organization", dict, List[Union["Organization", dict]]]] = None
    foundingDate: Optional[date] = None
    foundingLocation: Optional[dict] = None
    funder: Optional[Union["Organization", dict, List[Union["Organization", dict]]]] = None
    funding: Optional[Union[dict, List[dict]]] = None
    globalLocationNumber: Optional[str] = None
    hasCertification: Optional[Union[dict, List[dict]]] = None
    hasCredential: Optional[Union[dict, List[dict]]] = None
    hasGS1DigitalLink: Optional[HttpUrl] = None
    hasMemberProgram: Optional[dict] = None
    hasMerchantReturnPolicy: Optional[dict] = None
    hasOfferCatalog: Optional[dict] = None
    hasPOS: Optional[Union[dict, List[dict]]] = None
    hasShippingService: Optional[dict] = None
    interactionStatistic: Optional[Union[dict, List[dict]]] = None
    isicV4: Optional[str] = None
    iso6523Code: Optional[str] = None
    keywords: Optional[Union[str, dict, HttpUrl, List[Union[str, dict, HttpUrl]]]] = None
    knowsAbout: Optional[Union[str, dict, HttpUrl, List[Union[str, dict, HttpUrl]]]] = None
    knowsLanguage: Optional[Union[str, dict, List[Union[str, dict]]]] = None
    legalAddress: Optional[dict] = None
    legalName: Optional[str] = None
    legalRepresentative: Optional[Union[dict, List[dict]]] = None
    leiCode: Optional[str] = None
    location: Optional[Union[dict, str]] = None
    logo: Optional[Union[dict, HttpUrl]] = None
    makesOffer: Optional[Union[dict, List[dict]]] = None
    member: Optional[Union["Organization", dict, List[Union["Organization", dict]]]] = None
    memberOf: Optional[Union[dict, "Organization", List[Union[dict, "Organization"]]]] = None
    naics: Optional[str] = None
    nonprofitStatus: Optional[str] = None
    numberOfEmployees: Optional[dict] = None
    ownershipFundingInfo: Optional[Union[dict, str, HttpUrl]] = None
    owns: Optional[Union[dict, List[dict]]] = None
    parentOrganization: Optional["Organization"] = None
    publishingPrinciples: Optional[Union[dict, HttpUrl]] = None
    review: Optional[Union[dict, List[dict]]] = None
    seeks: Optional[Union[dict, List[dict]]] = None
    skills: Optional[Union[str, dict, List[Union[str, dict]]]] = None
    slogan: Optional[str] = None
    sponsor: Optional[Union["Organization", dict, List[Union["Organization", dict]]]] = None
    subOrganization: Optional[Union["Organization", List["Organization"]]] = None
    taxID: Optional[str] = None
    telephone: Optional[str] = None
    unnamedSourcesPolicy: Optional[Union[dict, HttpUrl]] = None
    vatID: Optional[str] = None

    # Properties from Thing
    additionalType: Optional[Union[str, HttpUrl]] = None
    alternateName: Optional[str] = None
    description: Optional[Union[str, dict]] = None
    disambiguatingDescription: Optional[str] = None
    identifier: Optional[Union[dict, str, HttpUrl]] = None
    image: Optional[Union[dict, HttpUrl]] = None
    mainEntityOfPage: Optional[Union[dict, HttpUrl]] = None
    name: Optional[str] = None
    owner: Optional[Union["Organization", dict]] = None
    potentialAction: Optional[Union[dict, List[dict]]] = None
    sameAs: Optional[Union[HttpUrl, List[HttpUrl]]] = None
    subjectOf: Optional[Union[dict, List[dict]]] = None
    url: Optional[HttpUrl] = None

    class Config:
        arbitrary_types_allowed = True


Organization.model_rebuild()