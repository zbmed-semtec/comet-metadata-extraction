from typing import Optional
from pydantic import Field
from app.layer_3.plugins.shared.types.json_ld_serializable import JsonLdSerializable

class OnlineAccount(JsonLdSerializable):
    """foaf:OnlineAccount - An online account.

    Represents the provision of some form of online service, by some party
    (indicated indirectly via accountServiceHomepage) to some Agent. The
    `account` property of an Agent is used to indicate accounts associated
    with that agent.

    Subclasses include: OnlineEcommerceAccount, OnlineGamingAccount,
    OnlineChatAccount.
    """

    accountName: Optional[str] = Field(
        default=None,
        description="Indicates a name given to an online account, which need not be the 'real' name of the Agent controlling the account."
    )
    accountServiceHomepage: Optional[str] = Field(
        default=None,
        description="Indicates a homepage for some item, e.g. a website, an organization, or an online account, that provides the service this account is associated with."
    )
    url: Optional[str] = None 