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

from talk_with_the_engineer.models.modelset_rules_of_thumb.region import (
    RegionInput,
    RegionNode,
    RegionOutput,
)

from talk_with_the_engineer.models.modelset_rules_of_thumb.supply import (
    SupplyInputGivenH,
    SupplyInputGivenSupply,
    SupplyOutput,
)


from talk_with_the_engineer.models.modelset_rules_of_thumb.allocation import (
    AllocationInput,
    AllocationNode,
    AllocationOutput,
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
    # region/systeemvraag
    "AllocationInput",
    "AllocationNode",
    "AllocationOutput",
    "RegionInput",
    "RegionNode",
    "RegionOutput",
]
