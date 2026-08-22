# rules of thumb
from talk_with_the_engineer.models.modelset_rules_of_thumb.retain import (
    RetentionInputGivenH,
    RetentionInputGivenArea,
    RetentionOutput,
)

from talk_with_the_engineer.models.modelset_rules_of_thumb.store import (
    StoreInputGivenArea,
    StoreInputGivenH,
    StoreOutput,
)

from talk_with_the_engineer.models.modelset_rules_of_thumb.discharge import (
    DischargeInputGivenH,
    DischargeInputGivenDischarge,
    DischargeOutput,
)

from talk_with_the_engineer.models.modelset_rules_of_thumb.supply import (
    SupplyInputGivenH,
    SupplyInputGivenSupply,
    SupplyOutput,
)


__all__ = [
    # rules of thumb
    # retention/vasthouden
    "RetentionInputGivenH",
    "RetentionInputGivenArea",
    "RetentionOutput",
    # store/storage/bergen
    "StoreInputGivenArea",
    "StoreInputGivenH",
    "StoreOutput",
    # discharge/afvoeren
    "DischargeInputGivenH",
    "DischargeInputGivenDischarge",
    "DischargeOutput",
    # supply/aanvoeren
    "SupplyInputGivenH",
    "SupplyInputGivenSupply",
    "SupplyOutput",
]
